import asyncio,json,struct,tempfile,unittest
from pathlib import Path
import broker as b
from test_broker import Client
class PortableTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_capabilities_species58_and_empty_fresh_rank(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fresh.sqlite3';broker=b.Broker(path)
            server=await asyncio.start_server(broker.accept,'127.0.0.1',0);port=server.sockets[0].getsockname()[1]
            clients=[]
            try:
                for nick in ['PortableHost','PortableGuest']:
                    r,w=await asyncio.open_connection('127.0.0.1',port);c=Client(r,w);clients.append(c)
                    await c.send(b.HELLO,struct.pack('>H',b.PROTOCOL)+b.string(nick)+b.string(b.BROKER_VERSION));await c.until(b.WELCOME)
                h,g=clients
                await h.send(b.QUERY_CAPABILITIES);self.assertEqual(await h.until(b.CAPABILITIES),struct.pack('>i',7))
                await h.send(b.GET_LEADERBOARD);self.assertEqual(await h.until(b.LEADERBOARD),b'\0\0')
                await h.send(b.CREATE,b.string('Portable58'));room=struct.unpack('>i',(await h.until(b.LOBBY))[:4])[0]
                await g.send(b.JOIN,struct.pack('>i',room));await g.until(b.LOBBY)
                await h.send(b.TEAMS,struct.pack('>ii',58,1));await h.until(b.LOBBY);await g.until(b.LOBBY)
                self.assertEqual(broker.rooms[room].host_team,58)
                await h.send(b.READY,b'\1');await g.send(b.READY,b'\1')
                hs=await h.until(b.START);gs=await g.until(b.START)
                self.assertEqual(struct.unpack('>iii',hs[:-1])[1:],(58,1));self.assertEqual(hs[:-1],gs[:-1])
                match_id=struct.unpack('>i',hs[:4])[0]
                result=struct.pack('>iii',match_id,2,1)
                await h.send(b.RESULT,result)
                self.assertEqual(struct.unpack('>ii',await h.until(b.RESULT_STATUS)),(match_id,1))
                await g.send(b.RESULT,result)
                self.assertEqual(struct.unpack('>ii',await h.until(b.RESULT_STATUS)),(match_id,2))
                self.assertEqual(struct.unpack('>ii',await g.until(b.RESULT_STATUS)),(match_id,2))
                await h.send(b.GET_LEADERBOARD)
                rank=await h.until(b.LEADERBOARD)
                self.assertEqual(struct.unpack('>H',rank[:2])[0],2)
            finally:
                for c in clients:await c.close()
                server.close();await server.wait_closed()
                for _ in range(100):
                    if not broker.peers:break
                    await asyncio.sleep(.01)
                broker.store.close()
            reopened=b.StatsStore(path)
            self.assertEqual(reopened.rows()[0][1:5],('PortableHost',1,0,0))
            reopened.close()
    async def test_local_and_lan_profiles_use_distinct_ports_and_ledgers(self):
        # Ephemeral analogue of shipping27888 local +27889 LAN: no firewall or
        # production port touched. Only loopback clients are used here.
        with tempfile.TemporaryDirectory() as tmp:
            a=b.Broker(Path(tmp)/'local.sqlite3');c=b.Broker(Path(tmp)/'lan.sqlite3')
            sa=await asyncio.start_server(a.accept,'127.0.0.1',0)
            # Bind only loopback in QA, avoiding any external listener or
            # possible firewall prompt while the user plays another game.
            sc=await asyncio.start_server(c.accept,'127.0.0.1',0)
            try:
                self.assertNotEqual(sa.sockets[0].getsockname()[1],sc.sockets[0].getsockname()[1])
                self.assertNotEqual(a.store.db,c.store.db)
                self.assertEqual(a.store.rows(),[]);self.assertEqual(c.store.rows(),[])
            finally:
                sa.close();sc.close();await sa.wait_closed();await sc.wait_closed();a.store.close();c.store.close()
