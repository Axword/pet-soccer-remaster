"""Isolated SQLite/result/leaderboard checks. Never uses the installed broker or game."""
import asyncio
from pathlib import Path
import struct
import tempfile
import unittest
import broker as b
from test_broker import Client


def unpack_stats(data):
    rd = b.Reader(data)
    nick = rd.text(48)
    values = tuple(rd.number() for _ in range(7))
    rd.end()
    return (nick,) + values


class LeaderboardProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "isolated.sqlite3"
        self.broker = b.Broker(self.path)
        self.server = await asyncio.start_server(self.broker.accept, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        self.clients = []

    async def asyncTearDown(self):
        for client in self.clients:
            await client.close()
        self.server.close()
        await self.server.wait_closed()
        for _ in range(100):
            if not self.broker.peers:
                break
            await asyncio.sleep(.01)
        self.assertEqual(self.broker.peers, {})
        self.broker.store.close()
        self.temp.cleanup()

    async def connect(self, nick):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        client = Client(reader, writer)
        self.clients.append(client)
        await client.send(b.HELLO, struct.pack(">H", b.PROTOCOL) + b.string(nick) + b.string("GMWL-6fbcaedb-online5"))
        await client.until(b.WELCOME)
        return client

    async def start(self, host, guest):
        await host.send(b.CREATE, b.string("Leaderboard test"))
        room_id = struct.unpack(">i", (await host.until(b.LOBBY))[:4])[0]
        await guest.send(b.JOIN, struct.pack(">i", room_id))
        await guest.until(b.LOBBY)
        await host.send(b.READY, b"\1")
        await guest.send(b.READY, b"\1")
        host_start = await host.until(b.START)
        guest_start = await guest.until(b.START)
        self.assertEqual(host_start[:-1], guest_start[:-1])
        return struct.unpack(">iii", host_start[:-1])[0]

    async def report(self, client, match_id, host_goals, guest_goals):
        await client.send(b.RESULT, struct.pack(">iii", match_id, host_goals, guest_goals))
        return struct.unpack(">ii", await client.until(b.RESULT_STATUS))

    async def complete(self, host, guest, match_id, host_goals, guest_goals):
        self.assertEqual(await self.report(host, match_id, host_goals, guest_goals), (match_id, 1))
        self.assertEqual(await self.report(guest, match_id, host_goals, guest_goals), (match_id, 2))
        self.assertEqual(struct.unpack(">ii", await host.until(b.RESULT_STATUS)), (match_id, 2))
        host_stats = unpack_stats(await host.until(b.SELF_STATS))
        guest_stats = unpack_stats(await guest.until(b.SELF_STATS))
        return host_stats, guest_stats

    async def test_win_draw_loss_duplicate_and_host_guest_score_order(self):
        host, guest = await self.connect("Alice"), await self.connect("Bob")
        expected = [((1, 0, 0, 1, 3, 10000), (0, 0, 1, 1, 0, 0)),
                    ((1, 1, 0, 2, 4, 5000), (0, 1, 1, 2, 1, 0)),
                    ((1, 1, 1, 3, 4, 3333), (1, 1, 1, 3, 4, 3333))]
        for goals, stats in zip(((4, 2), (3, 3), (1, 5)), expected):
            match_id = await self.start(host, guest)
            hs, gs = await self.complete(host, guest, match_id, *goals)
            self.assertEqual(hs[2:], stats[0])
            self.assertEqual(gs[2:], stats[1])
            self.assertEqual(await self.report(host, match_id, *goals), (match_id, 2))
            self.assertEqual(unpack_stats(await host.until(b.SELF_STATS))[2:], stats[0])
            # The duplicate causes fresh status/stats on the other peer too.
            await guest.until(b.RESULT_STATUS)
            await guest.until(b.SELF_STATS)
            await host.send(b.RESULT, struct.pack(">iii", match_id, goals[0] + 1, goals[1]))
            self.assertIn(b"Conflicting completed", await host.until(b.ERROR))
            self.assertEqual(self.broker.store.stats("alice")[1][2:], stats[0])
            await host.send(b.LEAVE)
            await host.until(b.LEFT)
            await guest.until(b.LEFT)
        await host.send(b.GET_LEADERBOARD)
        data = await host.until(b.LEADERBOARD)
        rd = b.Reader(data)
        self.assertEqual(struct.unpack(">H", rd.take(2))[0], 2)
        self.assertEqual(rd.text(48), "Alice")  # tied W/D/L: stable normalized name order

    async def test_two_peers_required_disconnect_abandons_and_cannot_replay(self):
        host, guest = await self.connect("One"), await self.connect("Two")
        match_id = await self.start(host, guest)
        self.assertEqual(await self.report(host, match_id, 9, 0), (match_id, 1))
        self.assertEqual(self.broker.store.stats("one")[1][5], 0)
        await guest.close()
        await host.until(b.LOBBY)
        await host.send(b.RESULT, struct.pack(">iii", match_id, 9, 0))
        self.assertIn(b"active match", await host.until(b.ERROR))
        self.assertEqual(self.broker.store.stats("one")[1][5], 0)
        self.assertEqual(self.broker.store.db.execute("SELECT state FROM matches WHERE id=?", (match_id,)).fetchone(), ("abandoned",))

    async def test_conflict_is_terminal_never_scores(self):
        host, guest = await self.connect("One"), await self.connect("Two")
        match_id = await self.start(host, guest)
        await self.report(host, match_id, 2, 0)
        self.assertEqual(await self.report(guest, match_id, 0, 2), (match_id, 3))
        self.assertEqual(struct.unpack(">ii", await host.until(b.RESULT_STATUS)), (match_id, 3))
        self.assertEqual(await self.report(guest, match_id, 2, 0), (match_id, 3))
        self.assertEqual(self.broker.store.stats("one")[1][5], 0)
        self.assertEqual(self.broker.store.db.execute("SELECT state FROM matches WHERE id=?", (match_id,)).fetchone(), ("conflict",))

    async def test_bad_scores_match_ids_extra_data_and_own_stats_query_quota(self):
        host, guest = await self.connect("Bounds"), await self.connect("Other")
        match_id = await self.start(host, guest)
        for payload in (struct.pack(">iii", match_id, -1, 0), struct.pack(">iii", match_id, 1000, 0),
                        struct.pack(">iii", match_id + 1, 1, 0), struct.pack(">iii", match_id, 1, 0) + b"x"):
            await host.send(b.RESULT, payload)
            await host.until(b.ERROR)
        await host.send(b.GET_SELF_STATS)
        self.assertEqual(unpack_stats(await host.until(b.SELF_STATS)), ("Bounds", 0, 0, 0, 0, 0, 0, 0))
        await host.send(b.GET_SELF_STATS)
        self.assertIn(b"query limit", await host.until(b.ERROR))
        self.assertEqual(self.broker.rooms[1].results, {})

    async def test_case_insensitive_profiles_same_nickname_cannot_play_itself(self):
        host, guest = await self.connect("Alice"), await self.connect("aLiCe")
        await host.send(b.CREATE, b.string("Name test"))
        room_id = struct.unpack(">i", (await host.until(b.LOBBY))[:4])[0]
        await guest.send(b.JOIN, struct.pack(">i", room_id))
        self.assertIn(b"different nicknames", await guest.until(b.ERROR))
        spaced = await self.connect("  ALICE ")
        await spaced.send(b.JOIN, struct.pack(">i", room_id))
        self.assertIn(b"different nicknames", await spaced.until(b.ERROR))
        self.assertEqual(self.broker.store.db.execute("SELECT COUNT(*) FROM players").fetchone(), (1,))

    async def test_leave_before_second_attestation_abandons_without_count(self):
        host, guest = await self.connect("Leaving"), await self.connect("Waiting")
        match_id = await self.start(host, guest)
        await self.report(host, match_id, 5, 0)
        await host.send(b.LEAVE)
        await host.until(b.LEFT)
        await guest.until(b.LEFT)
        await guest.send(b.RESULT, struct.pack(">iii", match_id, 5, 0))
        self.assertIn(b"active match", await guest.until(b.ERROR))
        self.assertEqual(self.broker.store.stats("leaving")[1][5], 0)
        self.assertEqual(self.broker.store.stats("waiting")[1][5], 0)

    async def test_final_snapshot_precedes_result_ack_byte_for_byte(self):
        host, guest = await self.connect("OrderedHost"), await self.connect("OrderedGuest")
        match_id = await self.start(host, guest)
        final = b"opaque-fulltime-state\0\xff" + struct.pack(">iii", match_id, 7, 2)
        await host.send(b.SNAPSHOT, final)
        await host.send(b.RESULT, struct.pack(">iii", match_id, 7, 2))
        self.assertEqual(await guest.until(b.SNAPSHOT), final)
        self.assertEqual(struct.unpack(">ii", await host.until(b.RESULT_STATUS)), (match_id, 1))
        self.assertEqual(await self.report(guest, match_id, 7, 2), (match_id, 2))

    async def test_failed_second_listener_does_not_abandon_running_ledger(self):
        host, guest = await self.connect("RunningHost"), await self.connect("RunningGuest")
        match_id = await self.start(host, guest)
        class Args:
            bind = "127.0.0.1"
            port = self.port
            db = self.path
        with self.assertRaises(OSError):
            await b.serve(Args())
        self.assertEqual(self.broker.store.db.execute("SELECT state FROM matches WHERE id=?", (match_id,)).fetchone(), ("started",))


class PersistentLedgerTests(unittest.TestCase):
    def test_restart_persists_results_ids_and_abandonment(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stats.sqlite3"
            store = b.StatsStore(path)
            host, guest = store.profile("ALICE"), store.profile("Bob")
            first = store.start(host, guest)
            self.assertTrue(store.complete(first, host, guest, (2, 1)))
            self.assertFalse(store.complete(first, host, guest, (2, 1)))
            with self.assertRaises(ValueError):
                store.complete(first, host, guest, (1, 2))
            abandoned = store.start(host, guest)
            store.close()
            store = b.StatsStore(path)
            self.assertEqual(store.profile("alice"), host)
            self.assertEqual(store.stats(host)[1][2:], (1, 0, 0, 1, 3, 10000))
            self.assertEqual(store.stats(guest)[1][2:], (0, 0, 1, 1, 0, 0))
            with self.assertRaises(ValueError):
                store.complete(abandoned, host, guest, (99, 0))
            self.assertGreater(store.start(host, guest), abandoned)
            self.assertFalse(store.complete(first, host, guest, (2, 1)))
            store.close()

    def test_sort_points_wins_exact_winrate_then_name_and_top50(self):
        store = b.StatsStore()
        for nick, wins, draws, losses in (("Low", 0, 0, 1), ("More", 2, 0, 9),
                                         ("Alpha", 1, 0, 1), ("Beta", 1, 0, 0),
                                         ("Draws", 0, 3, 0), ("Gamma", 1, 0, 0)):
            key = store.profile(nick)
            with store.db:
                store.db.execute("UPDATE players SET wins=?,draws=?,losses=? WHERE player_key=?", (wins, draws, losses, key))
        self.assertEqual([row[1] for row in store.rows()], ["More", "Beta", "Gamma", "Alpha", "Draws", "Low"])
        self.assertEqual(store.stats("low")[0], 6)
        for n in range(60):
            key = store.profile("Player%02d" % n)
            with store.db:
                store.db.execute("UPDATE players SET wins=1 WHERE player_key=?", (key,))
        self.assertEqual(len(store.rows()[:b.MAX_LEADERBOARD]), 50)
        self.assertGreater(store.stats("low")[0], 50)
        store.close()

    def test_ascii_identity_and_integer_capacity_rollback(self):
        for invalid in ("", "   ", "x" * 49, "N\x01", "Łukasz"):
            with self.assertRaises(ValueError):
                b.nick_key(invalid)
        store = b.StatsStore()
        host, guest = store.profile("Host"), store.profile("Guest")
        with store.db:
            store.db.execute("UPDATE players SET wins=? WHERE player_key=?", (b.MAX_MATCH_ID // 3, host))
        match_id = store.start(host, guest)
        with self.assertRaises(ValueError):
            store.complete(match_id, host, guest, (1, 0))
        self.assertEqual(store.db.execute("SELECT state FROM matches WHERE id=?", (match_id,)).fetchone(), ("started",))
        self.assertEqual(store.stats(guest)[1][5], 0)
        store.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
