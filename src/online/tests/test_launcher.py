"""Compile/test the launcher probe only. No UI/game launch or port27888 use."""
from pathlib import Path
import importlib.util
import json
import socket
import struct
import subprocess
import sys
import threading
import time
import unittest

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
EXE=HERE/'probe_test.exe'
VERSION=b'GMWL-6fbcaedb-online5'


def stats_response(nick=b'LauncherProbe',values=(0,0,0,0,0,0,0)):
    body=b'\x15'+struct.pack('>H',len(nick))+nick+struct.pack('>7i',*values)
    return struct.pack('>I',len(body))+body


def compile_probe():
    sys.path.insert(0,str(HERE.parent))
    from build_launcher import compile_cpp
    compile_cpp(HERE/'probe_test.cpp',EXE,console=True)


def read_exact(connection,count):
    data=b''
    while len(data)<count:
        value=connection.recv(count-len(data))
        if not value:raise AssertionError('probe closed before HELLO complete')
        data+=value
    return data


class ProbeTests(unittest.TestCase):
    def run_case(self,response,expected,fragment=False,hold=False,stats=None,stats_hold=False,caps=None,caps_hold=False):
        errors=[]
        with socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(2)
            port=server.getsockname()[1]
            self.assertNotEqual(port,27888)
            def peer():
                try:
                    with server.accept()[0] as connection:
                        connection.settimeout(2)
                        size=struct.unpack('>I',read_exact(connection,4))[0]
                        hello=read_exact(connection,size)
                        expected_hello=b'\x01\x00\x01'+struct.pack('>H',13)+b'LauncherProbe'+struct.pack('>H',len(VERSION))+VERSION
                        if hello!=expected_hello:raise AssertionError('incorrect protocol/build HELLO: '+repr(hello))
                        if response:
                            if fragment:
                                for value in response:
                                    connection.sendall(bytes([value]));time.sleep(.005)
                            else:connection.sendall(response)
                        valid_welcome=len(response)==9 and response[:5]==b'\0\0\0\x05\x02' and 0<int.from_bytes(response[5:],'big')<0x80000000
                        if valid_welcome:
                            request=read_exact(connection,5)
                            if request!=b'\0\0\0\x01\x14':raise AssertionError('missing bounded statistics capability request')
                            connection.sendall(stats_response() if stats is None else stats)
                            if stats_hold:time.sleep(.4)
                            if stats is None or expected:
                                request=read_exact(connection,5)
                                if request!=b'\0\0\0\x01\x1a':raise AssertionError('missing capabilities request')
                                connection.sendall(struct.pack('>IBi',5,27,7) if caps is None else caps)
                                if caps_hold:time.sleep(.4)
                        if hold:time.sleep(.4)
                        else:
                            try:
                                if connection.recv(1)!=b'':raise AssertionError('unexpected extra probe commands')
                            except ConnectionResetError:pass
                except (BrokenPipeError,ConnectionResetError):pass
                except BaseException as error:errors.append(error)
            thread=threading.Thread(target=peer,daemon=True);thread.start()
            begin=time.monotonic()
            result=subprocess.run([str(EXE),str(port)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=2,creationflags=subprocess.CREATE_NO_WINDOW)
            elapsed=time.monotonic()-begin
            thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors,repr(errors))
            self.assertEqual(result.returncode,0 if expected else 1,result.stdout)
            self.assertLess(elapsed,1.2,'probe exceeded small deadline')

    def test_valid_welcome_and_clean_shutdown(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',True)
    def test_fragmented_welcome(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x09',True,fragment=True)
    def test_http_service_rejected(self):self.run_case(b'HTTP/1.1 200 OK\r\n\r\n',False)
    def test_silent_service_times_out(self):self.run_case(b'',False,hold=True)
    def test_zero_length_rejected(self):self.run_case(struct.pack('>I',0),False)
    def test_oversize_length_rejected(self):self.run_case(struct.pack('>I',65537),False)
    def test_wrong_type_rejected(self):self.run_case(struct.pack('>I',5)+b'\x0b\0\0\0\x01',False)
    def test_zero_peer_id_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\0',False)
    def test_negative_peer_id_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\xff\xff\xff\xff',False)
    def test_truncated_welcome_times_out(self):self.run_case(struct.pack('>I',5)+b'\x02\0',False,hold=True)
    def test_old_broker_welcome_but_no_stats_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,stats=struct.pack('>I',6)+b'\x0b\0\x03old')
    def test_invalid_stats_count_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,stats=stats_response(values=(1,1,0,0,2,3,10000)))
    def test_truncated_stats_times_out(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,stats=b'\0\0\0\x2c\x15\0',stats_hold=True)
    def test_oversized_stats_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,stats=struct.pack('>I',65537))
    def test_valid_ranked_stats(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',True,stats=stats_response(values=(1,2,1,1,4,7,5000)))
    def test_stats_pause_without_species58_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,caps=struct.pack('>IBi',5,27,3))
    def test_stats_only_broker_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,caps=struct.pack('>IBi',5,27,1))
    def test_wrong_capability_type_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,caps=struct.pack('>IBi',5,11,3))
    def test_truncated_capabilities_times_out(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,caps=b'\0\0\0\x05\x1b',caps_hold=True)
    def test_oversized_capabilities_rejected(self):self.run_case(struct.pack('>I',5)+b'\x02\0\0\0\x01',False,caps=struct.pack('>I',65537))


if __name__=='__main__':
    compile_probe()
    with (HERE/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProbeTests))
    print((HERE/'tests.log').read_text(encoding='utf-8'))
    sys.exit(not result.wasSuccessful())
