#!/usr/bin/env python3
"""Pet Soccer Online 1v1 prototype relay. Python 3.10+, standard library only.

All peers connect outbound. This is a deliberately unauthenticated prototype,
not a production Internet service. See PROTOCOL.md before exposing it.
"""
import argparse
import asyncio
import logging
import math
import sqlite3
import struct
import time
from collections import deque
from fractions import Fraction
from pathlib import Path

PROTOCOL = 1
MAX_FRAME = 65536
MAX_DATA = 60000
MAX_QUEUE_BYTES = 262144
MAX_QUEUE_FRAMES = 128
MAX_CLIENTS = 128
MAX_ROOMS = 64
VALID_TEAMS = frozenset(range(12)) | {30, 37, 44, 51, 58}
HELLO, WELCOME, LIST, ROOMS, CREATE, JOIN, LEAVE, READY, LOBBY = range(1, 10)
LEFT, ERROR, SNAPSHOT, INPUT, PING, PONG, TEAMS, START = range(10, 18)
GET_LEADERBOARD, LEADERBOARD, GET_SELF_STATS, SELF_STATS, RESULT, RESULT_STATUS = range(18, 24)
PAUSE_REQUEST, PAUSE_STATE, QUERY_CAPABILITIES, CAPABILITIES = range(24, 28)
CAPABILITY_STATS = 1
CAPABILITY_PAUSE = 2
CAPABILITY_EXPANSION = 4
BROKER_VERSION = "GMWL-6fbcaedb-online5"
PAUSE_MILLIS = 15000
MAX_LEADERBOARD = 50
MAX_GOALS = 999
MAX_MATCH_ID = 2147483647
DEFAULT_DB = Path(__file__).resolve().parent / "data" / "leaderboard.sqlite3"


def nick_key(nick):
    """Existing prototype ASCII pseudonyms, case-insensitive; no account claim."""
    value = nick.strip()
    if not 1 <= len(value) <= 48 or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise ValueError("Nickname must use 1..48 printable ASCII characters")
    return value.lower()


class StatsStore:
    """Small broker-local ledger; completion and both W/D/L updates are atomic."""
    def __init__(self, path=":memory:"):
        if str(path) != ":memory:":
            Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), timeout=1.0)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                player_key TEXT PRIMARY KEY, nick TEXT NOT NULL,
                wins INTEGER NOT NULL DEFAULT 0, draws INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_key TEXT NOT NULL, guest_key TEXT NOT NULL,
                state TEXT NOT NULL, host_goals INTEGER, guest_goals INTEGER);
        """)
        # A restarted broker cannot resume its sockets/matches. Never score them later.
        with self.db:
            self.db.execute("UPDATE matches SET state='abandoned' WHERE state='started'")

    def profile(self, nick):
        key = nick_key(nick)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO players(player_key,nick) VALUES (?,?)", (key, nick.strip()))
        return key

    def start(self, host, guest):
        with self.db:
            cursor = self.db.execute("INSERT INTO matches(host_key,guest_key,state) VALUES (?,?,'started')", (host, guest))
            if cursor.lastrowid > MAX_MATCH_ID:
                raise ValueError("Match ID capacity reached")
            return cursor.lastrowid

    def cancel(self, match_id, state="abandoned"):
        if match_id:
            with self.db:
                self.db.execute("UPDATE matches SET state=? WHERE id=? AND state='started'", (state, match_id))

    def complete(self, match_id, host, guest, goals):
        with self.db:
            row = self.db.execute("SELECT host_key,guest_key,state,host_goals,guest_goals FROM matches WHERE id=?", (match_id,)).fetchone()
            if not row or row[:2] != (host, guest):
                raise ValueError("Unknown match participants")
            if row[2] == "completed":
                if row[3:] != goals:
                    raise ValueError("Conflicting completed result")
                return False
            if row[2] != "started":
                raise ValueError("Match was abandoned or conflicted")
            self.db.execute("UPDATE matches SET state='completed',host_goals=?,guest_goals=? WHERE id=?", goals + (match_id,))
            host_column, guest_column = (("wins", "losses") if goals[0] > goals[1]
                                         else ("losses", "wins") if goals[0] < goals[1]
                                         else ("draws", "draws"))
            for key, column in ((host, host_column), (guest, guest_column)):
                # Column choices are fixed above, never client text.
                self.db.execute("UPDATE players SET " + column + "=" + column + "+1 WHERE player_key=?", (key,))
                values = self.db.execute("SELECT wins,draws,losses FROM players WHERE player_key=?", (key,)).fetchone()
                if max(values + (sum(values), 3 * values[0] + values[1])) > MAX_MATCH_ID:
                    raise ValueError("Player statistic capacity reached")
            return True

    def rows(self):
        rows = []
        for key, nick, wins, draws, losses in self.db.execute("SELECT player_key,nick,wins,draws,losses FROM players WHERE wins+draws+losses>0"):
            games = wins + draws + losses
            rows.append((key, nick, wins, draws, losses, games, 3 * wins + draws, 10000 * wins // games))
        rows.sort(key=lambda r: (-r[6], -r[2], -Fraction(r[2], r[5]), r[0]))
        return rows

    def stats(self, key):
        for rank, row in enumerate(self.rows(), 1):
            if row[0] == key:
                return rank, row
        row = self.db.execute("SELECT player_key,nick,wins,draws,losses FROM players WHERE player_key=?", (key,)).fetchone()
        if not row:
            raise ValueError("Unknown player")
        return 0, row + (0, 0, 0)

    def close(self):
        self.db.close()


def stats_bytes(rank, row):
    # Limit every field to a signed Java int even for a very long-lived database.
    values = (rank,) + row[2:]
    if any(value < 0 or value > MAX_MATCH_ID for value in values):
        raise ValueError("Player statistic capacity reached")
    return string(row[1]) + struct.pack(">iiiiiii", *values)


def string(value):
    data = value.encode("utf-8")
    if len(data) > 1024:
        raise ValueError("string too long")
    return struct.pack(">H", len(data)) + data


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, count):
        if self.pos + count > len(self.data):
            raise ValueError("truncated frame")
        out = self.data[self.pos:self.pos + count]
        self.pos += count
        return out

    def number(self):
        return struct.unpack(">i", self.take(4))[0]

    def boolean(self):
        value = self.take(1)[0]
        if value not in (0, 1):
            raise ValueError("invalid boolean")
        return bool(value)

    def text(self, limit):
        size = struct.unpack(">H", self.take(2))[0]
        if size > limit:
            raise ValueError("string too long")
        value = self.take(size).decode("utf-8", "strict")
        if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("empty/control text")
        return value

    def end(self):
        if self.pos != len(self.data):
            raise ValueError("unexpected frame content")


class Peer:
    def __init__(self, broker, reader, writer, peer_id):
        self.broker, self.reader, self.writer, self.id = broker, reader, writer, peer_id
        self.nick = self.version = ""
        self.key = ""
        self.last_stats_query = {}
        self.room = None
        self.queue = deque()
        self.queued_bytes = 0
        self.wakeup = asyncio.Event()
        self.closed = False

    def send(self, kind, body=b""):
        if self.closed:
            return False
        payload = bytes([kind]) + body
        # A slow guest only needs the newest untransmitted authoritative state.
        if kind == SNAPSHOT:
            for index, queued in enumerate(self.queue):
                if queued[0] == SNAPSHOT:
                    self.queued_bytes -= len(queued) + 4
                    del self.queue[index]
                    break
        size = len(payload) + 4
        if len(payload) > MAX_FRAME or len(self.queue) >= MAX_QUEUE_FRAMES or self.queued_bytes + size > MAX_QUEUE_BYTES:
            self.close("outbound queue limit")
            return False
        self.queue.append(payload)
        self.queued_bytes += size
        self.wakeup.set()
        return True

    def close(self, reason):
        if self.closed:
            return
        self.closed = True
        self.queue.clear()
        self.queued_bytes = 0
        self.wakeup.set()
        self.writer.close()
        logging.info("peer %d disconnected: %s", self.id, reason)

    async def write_loop(self):
        try:
            while not self.closed:
                await self.wakeup.wait()
                while self.queue and not self.closed:
                    payload = self.queue.popleft()
                    self.queued_bytes -= len(payload) + 4
                    self.writer.write(struct.pack(">I", len(payload)) + payload)
                    await asyncio.wait_for(self.writer.drain(), 5.0)
                self.wakeup.clear()
        except (ConnectionError, OSError, asyncio.TimeoutError):
            self.close("write timeout or error")

    async def frame(self, timeout):
        header = await asyncio.wait_for(self.reader.readexactly(4), timeout)
        size = struct.unpack(">I", header)[0]
        if not 1 <= size <= MAX_FRAME:
            raise ValueError("frame size limit")
        payload = await asyncio.wait_for(self.reader.readexactly(size), 10.0)
        return payload[0], Reader(payload[1:])


class Room:
    def __init__(self, room_id, name, host):
        self.id, self.name, self.host = room_id, name, host
        self.guest = None
        self.host_ready = self.guest_ready = self.started = False
        self.host_team, self.guest_team = 0, 1
        self.match_id = 0
        self.results = {}
        self.result_status = 0
        self.pause_until = 0.0
        self.pause_timer = None

    def details(self):
        return (struct.pack(">i", self.id) + string(self.name) + string(self.host.version)
                + string(self.host.nick) + string(self.guest.nick if self.guest else "")
                + bytes([self.host_ready, self.guest_ready, self.started])
                + struct.pack(">iii", self.host_team, self.guest_team, self.match_id))


class Broker:
    def __init__(self, db_path=":memory:"):
        self.peers, self.rooms = {}, {}
        self.next_peer = self.next_room = 1
        self.store = StatsStore(db_path)

    def update(self, room):
        for peer in (room.host, room.guest):
            if peer:
                peer.send(LOBBY, room.details() + bytes([peer is room.host]))

    def clear_pause(self, room, notify=False):
        if room.pause_timer:
            room.pause_timer.cancel()
            room.pause_timer = None
        was_paused = room.pause_until > 0
        room.pause_until = 0.0
        if notify and was_paused:
            data = struct.pack(">i?i", room.match_id, False, 0)
            for target in (room.host, room.guest):
                if target:
                    target.send(PAUSE_STATE, data)

    def resume_pause(self, room, match_id):
        # The timer must not affect a replacement room or a later match.
        if self.rooms.get(room.id) is not room or not room.started or room.match_id != match_id:
            return
        self.clear_pause(room, notify=True)

    def request_pause(self, peer):
        room = peer.room
        if (not room or not room.started or not room.guest or room.result_status in (2, 3)
                or peer not in (room.host, room.guest)):
            raise ValueError("Pause requires an active match")
        loop = asyncio.get_running_loop()
        now = loop.time()
        if room.pause_until > now:
            # Held Escape or either player's repeated requests cannot extend it
            # or flood the outgoing queues with duplicate state packets.
            return
        self.clear_pause(room)
        room.pause_until = now + PAUSE_MILLIS / 1000.0
        room.pause_timer = loop.call_later(PAUSE_MILLIS / 1000.0, self.resume_pause, room, room.match_id)
        remaining = max(1, min(PAUSE_MILLIS, math.ceil((room.pause_until - loop.time()) * 1000)))
        data = struct.pack(">i?i", room.match_id, True, remaining)
        for target in (room.host, room.guest):
            target.send(PAUSE_STATE, data)

    def leave(self, peer, notify=True):
        room = peer.room
        if not room:
            if notify:
                peer.send(LEFT)
            return
        self.store.cancel(room.match_id)
        self.clear_pause(room)
        peer.room = None
        if peer is room.host:
            del self.rooms[room.id]
            if room.guest:
                guest = room.guest
                guest.room = None
                guest.send(LEFT, string("Host left; room closed"))
        else:
            room.guest = None
            room.host_ready = room.guest_ready = room.started = False
            room.match_id = 0
            room.results.clear()
            room.result_status = 0
            self.update(room)
        if notify:
            peer.send(LEFT)

    def handle(self, peer, kind, rd):
        if kind == LIST:
            rd.end()
            rooms = [r for r in self.rooms.values() if r.host.version == peer.version]
            peer.send(ROOMS, struct.pack(">H", len(rooms)) + b"".join(r.details() for r in rooms))
        elif kind == CREATE:
            name = rd.text(96)
            rd.end()
            if peer.room:
                raise ValueError("Leave current room first")
            if len(self.rooms) >= MAX_ROOMS:
                raise ValueError("Room limit reached")
            room = Room(self.next_room, name, peer)
            self.next_room += 1
            self.rooms[room.id] = room
            peer.room = room
            self.update(room)
        elif kind == JOIN:
            room_id = rd.number()
            rd.end()
            if peer.room:
                raise ValueError("Leave current room first")
            room = self.rooms.get(room_id)
            if not room or room.guest or room.started:
                raise ValueError("Room unavailable")
            if peer.version != room.host.version:
                raise ValueError("Game version mismatch")
            if peer.key == room.host.key:
                raise ValueError("Players need different nicknames")
            room.guest = peer
            peer.room = room
            room.host_ready = room.guest_ready = False
            self.update(room)
        elif kind == LEAVE:
            rd.end()
            self.leave(peer)
        elif kind == READY:
            ready = rd.boolean()
            rd.end()
            room = peer.room
            if not room or room.started:
                raise ValueError("Not in a waiting room")
            if peer is room.host:
                room.host_ready = ready
            else:
                room.guest_ready = ready
            if room.guest and room.host_ready and room.guest_ready:
                room.match_id = self.store.start(room.host.key, room.guest.key)
                room.started = True
                room.results.clear()
                room.result_status = 0
            self.update(room)
            if room.started:
                for target in (room.host, room.guest):
                    target.send(START, struct.pack(">iii", room.match_id, room.host_team, room.guest_team) + bytes([target is room.host]))
        elif kind == TEAMS:
            host_team, guest_team = rd.number(), rd.number()
            rd.end()
            room = peer.room
            if not room or room.started:
                raise ValueError("Only waiting players can select teams")
            if host_team not in VALID_TEAMS or guest_team not in VALID_TEAMS:
                raise ValueError("Invalid team")
            old = room.host_team, room.guest_team
            if peer is room.host:
                room.host_team = host_team
            else:
                room.guest_team = guest_team
            if old != (room.host_team, room.guest_team):
                room.host_ready = room.guest_ready = False
            self.update(room)
        elif kind in (SNAPSHOT, INPUT):
            data = rd.take(len(rd.data))
            room = peer.room
            if not room or not room.started or not room.guest:
                raise ValueError("Match not running")
            if not 1 <= len(data) <= MAX_DATA:
                raise ValueError("Opaque payload limit")
            if kind == SNAPSHOT and peer is room.host:
                room.guest.send(SNAPSHOT, data)
            elif kind == INPUT and peer is room.guest:
                # Paused movement must not replay on the host after resuming.
                if room.pause_until <= asyncio.get_running_loop().time():
                    room.host.send(INPUT, data)
            else:
                raise ValueError("Invalid relay direction")
        elif kind == PING:
            rd.end()
            peer.send(PONG)
        elif kind == QUERY_CAPABILITIES:
            rd.end()
            peer.send(CAPABILITIES, struct.pack(">i", CAPABILITY_STATS | CAPABILITY_PAUSE | CAPABILITY_EXPANSION))
        elif kind == PAUSE_REQUEST:
            rd.end()
            self.request_pause(peer)
        elif kind in (GET_LEADERBOARD, GET_SELF_STATS):
            rd.end()
            now = time.monotonic()
            if now - peer.last_stats_query.get(kind, -1000.0) < .25:
                raise ValueError("Statistics query limit; wait before refreshing")
            peer.last_stats_query[kind] = now
            if kind == GET_LEADERBOARD:
                rows = self.store.rows()[:MAX_LEADERBOARD]
                peer.send(LEADERBOARD, struct.pack(">H", len(rows)) + b"".join(stats_bytes(rank, row) for rank, row in enumerate(rows, 1)))
            else:
                peer.send(SELF_STATS, stats_bytes(*self.store.stats(peer.key)))
        elif kind == RESULT:
            match_id, host_goals, guest_goals = rd.number(), rd.number(), rd.number()
            rd.end()
            room = peer.room
            if not room or not room.started or not room.guest or match_id != room.match_id:
                raise ValueError("Result is not for the active match")
            if not 0 <= host_goals <= MAX_GOALS or not 0 <= guest_goals <= MAX_GOALS:
                raise ValueError("Result score limit")
            goals = host_goals, guest_goals
            old = room.results.get(peer.id)
            if room.result_status == 3 or (old is not None and old != goals):
                if room.result_status != 2:
                    room.result_status = 3
                    self.store.cancel(match_id, "conflict")
                else:
                    raise ValueError("Conflicting completed result")
            elif room.result_status != 2:
                room.results[peer.id] = goals
                if len(room.results) == 2:
                    if room.results[room.host.id] != room.results[room.guest.id]:
                        room.result_status = 3
                        self.store.cancel(match_id, "conflict")
                    else:
                        self.store.complete(match_id, room.host.key, room.guest.key, goals)
                        room.result_status = 2
                else:
                    room.result_status = 1
            if room.result_status in (2, 3):
                self.clear_pause(room, notify=True)
            targets = (room.host, room.guest) if room.result_status in (2, 3) else (peer,)
            for target in targets:
                target.send(RESULT_STATUS, struct.pack(">ii", match_id, room.result_status))
                if room.result_status == 2:
                    target.send(SELF_STATS, stats_bytes(*self.store.stats(target.key)))
        else:
            raise ValueError("Unsupported command")

    async def accept(self, reader, writer):
        if len(self.peers) >= MAX_CLIENTS:
            writer.close()
            await writer.wait_closed()
            return
        peer = Peer(self, reader, writer, self.next_peer)
        self.next_peer += 1
        self.peers[peer.id] = peer
        writer_task = asyncio.create_task(peer.write_loop())
        try:
            kind, rd = await peer.frame(5.0)
            if kind != HELLO or struct.unpack(">H", rd.take(2))[0] != PROTOCOL:
                raise ValueError("Protocol version mismatch")
            peer.nick, peer.version = rd.text(48), rd.text(80)
            rd.end()
            peer.key = self.store.profile(peer.nick)
            peer.send(WELCOME, struct.pack(">i", peer.id))
            while not peer.closed:
                kind, rd = await peer.frame(45.0)
                try:
                    self.handle(peer, kind, rd)
                except (ValueError, sqlite3.Error) as exc:
                    if isinstance(exc, sqlite3.Error):
                        logging.exception("Statistics database command failed")
                        exc = ValueError("Statistics storage unavailable")
                    peer.send(ERROR, string(str(exc)))
        except (asyncio.IncompleteReadError, ConnectionError, OSError, asyncio.TimeoutError, ValueError, UnicodeError) as exc:
            logging.debug("peer %d: %s", peer.id, exc)
        finally:
            self.leave(peer, notify=False)
            self.peers.pop(peer.id, None)
            peer.close("connection ended")
            writer_task.cancel()
            await asyncio.gather(writer_task, return_exceptions=True)
            try:
                await asyncio.wait_for(writer.wait_closed(), 1.0)
            except (OSError, asyncio.TimeoutError):
                pass


async def serve(args):
    broker = None
    async def accept(reader, writer):
        await broker.accept(reader, writer)
    # Claim the listening port before opening/recovering the ledger. A second
    # launcher must not abandon a running broker's matches merely by failing bind.
    server = await asyncio.start_server(accept, args.bind, args.port, limit=MAX_FRAME + 4, start_serving=False)
    try:
        broker = Broker(args.db)
        logging.info("Pet Soccer prototype broker listening on %s", ", ".join(str(s.getsockname()) for s in server.sockets))
        async with server:
            await server.serve_forever()
    finally:
        server.close()
        await server.wait_closed()
        if broker:
            # Remove rooms before closing the ledger. Later socket cleanup sees
            # peer.room=None and cannot write a closed database.
            for peer in list(broker.peers.values()):
                broker.leave(peer, notify=False)
                peer.close("broker shutdown")
            broker.store.close()


if __name__ == "__main__":
    if (Path(__file__).resolve().parent / "SOURCE_ONLY.md").is_file():
        raise SystemExit("Stage a workspace with tools/prepare_online_workspace.py; do not create server data in source directories.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1", help="LAN/VPS: explicitly select 0.0.0.0 or an interface address")
    parser.add_argument("--port", type=int, default=27888)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Broker-local SQLite leaderboard database (persistent by default)")
    parser.add_argument("--verbose", action="store_true")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if arguments.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(serve(arguments))
    except KeyboardInterrupt:
        pass
