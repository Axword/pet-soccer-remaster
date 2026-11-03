"""Shared pause tests: artificial peers, random loopback ports, in-memory DB only."""
import asyncio
import struct
import unittest

import broker as b
from test_broker import Client


class PauseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.broker = b.Broker()
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
        self.assertEqual(self.broker.rooms, {})
        self.broker.store.close()

    async def connect(self, nick):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        client = Client(reader, writer)
        self.clients.append(client)
        await client.send(b.HELLO, struct.pack(">H", b.PROTOCOL) + b.string(nick) + b.string("GMWL-6fbcaedb-online5"))
        await client.until(b.WELCOME)
        return client

    async def start(self):
        host, guest = await self.connect("Host"), await self.connect("Guest")
        await host.send(b.CREATE, b.string("Pause test"))
        room_id = struct.unpack(">i", (await host.until(b.LOBBY))[:4])[0]
        await guest.send(b.JOIN, struct.pack(">i", room_id))
        await guest.until(b.LOBBY)
        await host.send(b.READY, b"\1")
        await guest.send(b.READY, b"\1")
        host_start = await host.until(b.START)
        guest_start = await guest.until(b.START)
        self.assertEqual(host_start[:-1], guest_start[:-1])
        return host, guest, self.broker.rooms[room_id]

    async def pause(self, sender, host, guest, room):
        await sender.send(b.PAUSE_REQUEST)
        hp = await host.until(b.PAUSE_STATE)
        gp = await guest.until(b.PAUSE_STATE)
        self.assertEqual(hp, gp)
        match_id, paused, remaining = struct.unpack(">i?i", hp)
        self.assertEqual(match_id, room.match_id)
        self.assertTrue(paused)
        self.assertGreaterEqual(remaining, 14900)
        self.assertLessEqual(remaining, 15000)
        return hp

    async def test_capabilities_after_hello_and_payload_validation(self):
        peer = await self.connect("Probe")
        await peer.send(b.QUERY_CAPABILITIES)
        self.assertEqual(struct.unpack(">i", await peer.until(b.CAPABILITIES)), (7,))
        await peer.send(b.QUERY_CAPABILITIES, b"extra")
        self.assertIn(b"unexpected frame content", await peer.until(b.ERROR))
        await peer.send(b.PING)
        self.assertEqual(await peer.until(b.PONG), b"")

    async def test_only_started_participants_and_empty_pause_body(self):
        outsider = await self.connect("Outsider")
        await outsider.send(b.PAUSE_REQUEST)
        self.assertIn(b"active match", await outsider.until(b.ERROR))
        host, guest, room = await self.start()
        await outsider.send(b.PAUSE_REQUEST)
        self.assertIn(b"active match", await outsider.until(b.ERROR))
        await host.send(b.PAUSE_REQUEST, b"extra")
        self.assertIn(b"unexpected frame content", await host.until(b.ERROR))
        self.assertIsNone(room.pause_timer)
        await self.pause(guest, host, guest, room)

    async def test_both_peers_pause_real_15_seconds_spam_does_not_extend(self):
        host, guest, room = await self.start()
        loop = asyncio.get_running_loop()
        begin = loop.time()
        await self.pause(guest, host, guest, room)
        deadline, timer = room.pause_until, room.pause_timer
        self.assertAlmostEqual(deadline - begin, 15, delta=.25)
        for _ in range(20):
            await host.send(b.PAUSE_REQUEST)
            await guest.send(b.PAUSE_REQUEST)
        await host.send(b.PING)
        await guest.send(b.PING)
        await host.until(b.PONG)
        await guest.until(b.PONG)
        self.assertEqual(room.pause_until, deadline)
        self.assertIs(room.pause_timer, timer)
        # Drain direct frames with a bounded timeout long enough for 15 seconds;
        # Client.receive's usual two-second timeout is intentionally unchanged.
        async def resume(client):
            size = struct.unpack(">I", await asyncio.wait_for(client.reader.readexactly(4), 16))[0]
            frame = await asyncio.wait_for(client.reader.readexactly(size), 2)
            self.assertEqual(frame[0], b.PAUSE_STATE)
            return struct.unpack(">i?i", frame[1:])
        hp, gp = await asyncio.gather(resume(host), resume(guest))
        elapsed = loop.time() - begin
        self.assertEqual(hp, (room.match_id, False, 0))
        self.assertEqual(gp, hp)
        self.assertGreaterEqual(elapsed, 14.9)
        self.assertLess(elapsed, 16)
        self.assertEqual(room.pause_until, 0)
        self.assertIsNone(room.pause_timer)

    async def test_pause_drops_gameplay_input_keeps_control_and_snapshot(self):
        host, guest, room = await self.start()
        await self.pause(host, host, guest, room)
        await guest.send(b.INPUT, b"must-not-replay")
        await guest.send(b.PING)
        await guest.until(b.PONG)  # proves the earlier INPUT was processed
        await host.send(b.PING)
        self.assertEqual(await host.receive(), (b.PONG, b""))
        await host.send(b.SNAPSHOT, b"authoritative-state")
        self.assertEqual(await guest.until(b.SNAPSHOT), b"authoritative-state")
        self.broker.resume_pause(room, room.match_id)
        await host.until(b.PAUSE_STATE)
        await guest.until(b.PAUSE_STATE)
        await guest.send(b.INPUT, b"new-input")
        self.assertEqual(await host.until(b.INPUT), b"new-input")

    async def test_guest_leave_cancels_timer_new_match_not_affected(self):
        host, guest, room = await self.start()
        await self.pause(host, host, guest, room)
        timer, old_id = room.pause_timer, room.match_id
        await guest.send(b.LEAVE)
        await guest.until(b.LEFT)
        await host.until(b.LOBBY)
        self.assertTrue(timer.cancelled())
        self.assertEqual(room.pause_until, 0)
        self.assertIsNone(room.pause_timer)
        await guest.send(b.JOIN, struct.pack(">i", room.id))
        await guest.until(b.LOBBY)
        await host.send(b.READY, b"\1")
        await guest.send(b.READY, b"\1")
        await host.until(b.START)
        await guest.until(b.START)
        self.assertNotEqual(room.match_id, old_id)
        await self.pause(guest, host, guest, room)
        new_deadline, new_timer = room.pause_until, room.pause_timer
        self.broker.resume_pause(room, old_id)  # stale timer cannot clear new pause
        self.assertEqual(room.pause_until, new_deadline)
        self.assertIs(room.pause_timer, new_timer)

    async def test_host_disconnect_cancels_timer(self):
        host, guest, room = await self.start()
        await self.pause(guest, host, guest, room)
        timer = room.pause_timer
        await host.close()
        await guest.until(b.LEFT)
        self.assertNotIn(room.id, self.broker.rooms)
        self.assertTrue(timer.cancelled())
        self.assertIsNone(room.pause_timer)
        self.assertEqual(room.pause_until, 0)

    async def test_completed_or_conflicted_result_resumes_and_disallows_pause(self):
        for conflict in (False, True):
            host, guest, room = await self.start()
            await self.pause(host, host, guest, room)
            timer = room.pause_timer
            await host.send(b.RESULT, struct.pack(">iii", room.match_id, 1, 0))
            await host.until(b.RESULT_STATUS)
            await guest.send(b.RESULT, struct.pack(">iii", room.match_id, 0 if conflict else 1, 0))
            self.assertEqual(struct.unpack(">i?i", await host.until(b.PAUSE_STATE)), (room.match_id, False, 0))
            self.assertEqual(struct.unpack(">i?i", await guest.until(b.PAUSE_STATE)), (room.match_id, False, 0))
            expected = 3 if conflict else 2
            self.assertEqual(struct.unpack(">ii", await host.until(b.RESULT_STATUS)), (room.match_id, expected))
            self.assertEqual(struct.unpack(">ii", await guest.until(b.RESULT_STATUS)), (room.match_id, expected))
            self.assertTrue(timer.cancelled())
            self.assertIsNone(room.pause_timer)
            await host.send(b.PAUSE_REQUEST)
            self.assertIn(b"active match", await host.until(b.ERROR))
            await host.send(b.LEAVE)
            await host.until(b.LEFT)
            await guest.until(b.LEFT)


if __name__ == "__main__":
    unittest.main()
