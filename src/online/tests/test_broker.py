"""Meaningful protocol/relay tests; no game process, port or data is touched."""
import asyncio
import struct
import unittest
import broker as b


class Client:
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer

    async def send(self, kind, body=b""):
        payload = bytes([kind]) + body
        self.writer.write(struct.pack(">I", len(payload)) + payload)
        await self.writer.drain()

    async def receive(self):
        size = struct.unpack(">I", await asyncio.wait_for(self.reader.readexactly(4), 2))[0]
        data = await asyncio.wait_for(self.reader.readexactly(size), 2)
        return data[0], data[1:]

    async def until(self, kind):
        for _ in range(30):
            actual, body = await self.receive()
            if actual == kind:
                return body
        raise AssertionError("message not received: " + str(kind))

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()


class BrokerTests(unittest.IsolatedAsyncioTestCase):
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

    async def connect(self, nick, version="GMWL-6fbcaedb-online5"):
        reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", self.port), 3)
        client = Client(reader, writer)
        self.clients.append(client)
        await client.send(b.HELLO, struct.pack(">H", b.PROTOCOL) + b.string(nick) + b.string(version))
        self.assertEqual(len(await client.until(b.WELCOME)), 4)
        return client

    async def room(self):
        host, guest = await self.connect("Host"), await self.connect("Guest")
        await host.send(b.CREATE, b.string("Test room"))
        room_id = struct.unpack(">i", (await host.until(b.LOBBY))[:4])[0]
        await guest.send(b.JOIN, struct.pack(">i", room_id))
        await guest.until(b.LOBBY)
        await host.until(b.LOBBY)
        return host, guest, room_id

    async def start_match(self, host, guest):
        await host.send(b.READY, b"\x01")
        await guest.send(b.READY, b"\x01")
        host_start, guest_start = await host.until(b.START), await guest.until(b.START)
        self.assertEqual(host_start[:-1], guest_start[:-1])
        self.assertEqual((host_start[-1], guest_start[-1]), (1, 0))
        return struct.unpack(">iii", host_start[:-1])

    async def test_lobby_teams_ready_relay_disconnect(self):
        host, guest, room_id = await self.room()
        await host.send(b.TEAMS, struct.pack(">ii", 37, 44))
        await host.until(b.LOBBY)
        await guest.until(b.LOBBY)
        self.assertEqual((self.broker.rooms[room_id].host_team, self.broker.rooms[room_id].guest_team), (37, 1))
        await guest.send(b.TEAMS, struct.pack(">ii", 51, 30))
        await host.until(b.LOBBY)
        await guest.until(b.LOBBY)
        match_id, host_team, guest_team = await self.start_match(host, guest)
        self.assertEqual((host_team, guest_team), (37, 30))
        self.assertGreater(match_id, 0)
        snapshot = bytes(range(256)) * 200
        await host.send(b.SNAPSHOT, snapshot)
        self.assertEqual(await guest.until(b.SNAPSHOT), snapshot)
        controls = struct.pack(">iiii", 3, 7, -1, 1234)
        await guest.send(b.INPUT, controls)
        self.assertEqual(await host.until(b.INPUT), controls)
        await guest.send(b.SNAPSHOT, b"forged")
        self.assertIn(b"direction", await guest.until(b.ERROR))
        await host.send(b.INPUT, b"forged")
        self.assertIn(b"direction", await host.until(b.ERROR))
        await guest.close()
        await host.until(b.LOBBY)
        room = self.broker.rooms[room_id]
        self.assertFalse(room.started or room.host_ready or room.guest_ready)
        self.assertIsNone(room.guest)

    async def test_version_room_capacity_and_host_cleanup(self):
        host, guest, room_id = await self.room()
        third = await self.connect("Third")
        await third.send(b.JOIN, struct.pack(">i", room_id))
        self.assertIn(b"unavailable", await third.until(b.ERROR))
        old = await self.connect("Other", "Other-build")
        await old.send(b.LIST)
        self.assertEqual(await old.until(b.ROOMS), b"\0\0")
        await guest.send(b.LEAVE)
        await guest.until(b.LEFT)
        await host.until(b.LOBBY)
        await old.send(b.JOIN, struct.pack(">i", room_id))
        self.assertIn(b"mismatch", await old.until(b.ERROR))
        await guest.send(b.JOIN, struct.pack(">i", room_id))
        await guest.until(b.LOBBY)
        await host.until(b.LOBBY)
        await host.close()
        self.assertIn(b"Host left", await guest.until(b.LEFT))
        self.assertEqual(self.broker.rooms, {})

    async def test_team_change_cancels_readiness(self):
        host, guest, room_id = await self.room()
        await host.send(b.READY, b"\x01")
        await host.until(b.LOBBY)
        await guest.until(b.LOBBY)
        await guest.send(b.TEAMS, struct.pack(">ii", 51, 44))
        await host.until(b.LOBBY)
        await guest.until(b.LOBBY)
        room = self.broker.rooms[room_id]
        self.assertFalse(room.host_ready or room.guest_ready)
        self.assertEqual(room.host_team, 0)
        await guest.send(b.TEAMS, struct.pack(">ii", 0, 255))
        self.assertIn(b"Invalid team", await guest.until(b.ERROR))
        self.assertEqual(room.guest_team, 44)
        await host.send(b.SNAPSHOT, b"before-start")
        self.assertIn(b"not running", await host.until(b.ERROR))

    async def test_oversize_and_bad_protocol_close_without_allocation(self):
        reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", self.port), 3)
        self.clients.append(Client(reader, writer))
        writer.write(struct.pack(">I", b.MAX_FRAME + 1))
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")
        reader, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", self.port), 3)
        bad = Client(reader, writer)
        self.clients.append(bad)
        await bad.send(b.HELLO, struct.pack(">H", 99) + b.string("N") + b.string("V"))
        self.assertEqual(await asyncio.wait_for(reader.read(), 2), b"")

    async def test_fragmentation_ping_and_invalid_boolean(self):
        client = await self.connect("Fragment")
        payload = b"\x0e"
        wire = struct.pack(">I", len(payload)) + payload
        for byte in wire:
            client.writer.write(bytes([byte]))
            await client.writer.drain()
            await asyncio.sleep(.005)
        self.assertEqual(await client.until(b.PONG), b"")
        await client.send(b.READY, b"\x02")
        self.assertIn(b"boolean", await client.until(b.ERROR))

    async def test_payload_limit_error_does_not_poison_next_frame(self):
        host, guest, _ = await self.room()
        await self.start_match(host, guest)
        await host.send(b.SNAPSHOT, b"x" * (b.MAX_DATA + 1))
        self.assertIn(b"limit", await host.until(b.ERROR))
        await host.send(b.SNAPSHOT, b"next")
        self.assertEqual(await guest.until(b.SNAPSHOT), b"next")


class FakeWriter:
    closed = False
    def close(self):
        self.closed = True


class BackpressureTests(unittest.TestCase):
    def test_control_input_queue_overflow_disconnects_and_releases_memory(self):
        peer = b.Peer(None, None, FakeWriter(), 1)
        for _ in range(b.MAX_QUEUE_FRAMES):
            self.assertTrue(peer.send(b.INPUT, b"123"))
        self.assertFalse(peer.send(b.INPUT, b"overflow"))
        self.assertTrue(peer.closed and peer.writer.closed)
        self.assertEqual((len(peer.queue), peer.queued_bytes), (0, 0))

    def test_snapshot_queue_coalesces_latest_and_byte_limit_is_bounded(self):
        peer = b.Peer(None, None, FakeWriter(), 1)
        for i in range(1000):
            self.assertTrue(peer.send(b.SNAPSHOT, struct.pack(">i", i)))
        self.assertEqual(len(peer.queue), 1)
        self.assertEqual(peer.queue[0][1:], struct.pack(">i", 999))
        self.assertEqual(peer.queued_bytes, 9)
        peer = b.Peer(None, None, FakeWriter(), 2)
        for _ in range(4):
            self.assertTrue(peer.send(b.INPUT, b"x" * 60000))
        self.assertFalse(peer.send(b.INPUT, b"x" * 60000))
        self.assertTrue(peer.closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
