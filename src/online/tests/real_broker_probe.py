"""Actual packaged broker CLI + actual C++ health probe, no game/GUI."""
from pathlib import Path
import json,socket,subprocess,sys,tempfile,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT));from build_launcher import compile_cpp
runtime=ROOT/'payload/online/runtime/python.exe'
assert Path(sys.executable).resolve()==runtime.resolve()
exe=HERE/'real_broker_probe.exe';compile_cpp(HERE/'real_broker_probe.cpp',exe,console=True)
with socket.socket() as reserve:
    reserve.bind(('127.0.0.1',0));port=reserve.getsockname()[1]
assert port not in (27888,27889)
temporary=HERE/'temporary';temporary.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=temporary,prefix='cli-probe-') as tmp:
    folder=Path(tmp);db=folder/'fresh.sqlite3'
    with (folder/'broker.log').open('wb') as log:
        process=subprocess.Popen([str(runtime),'-I','-u',str(ROOT/'payload/online/broker.py'),'--bind','127.0.0.1','--port',str(port),'--db',str(db)],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        attempts=0;ready=False;begin=time.monotonic()
        try:
            while time.monotonic()-begin<15:
                assert process.poll() is None,'Owned broker CLI exited during startup'
                attempts+=1
                r=subprocess.run([str(exe),str(port)],capture_output=True,timeout=2,creationflags=subprocess.CREATE_NO_WINDOW)
                if r.returncode==0:ready=True;break
                time.sleep(.1)
            assert ready,'Current real broker did not pass actual launcher health within15s'
            warm=[]
            for _ in range(3):
                start=time.monotonic();r=subprocess.run([str(exe),str(port)],capture_output=True,timeout=2,creationflags=subprocess.CREATE_NO_WINDOW)
                assert r.returncode==0;warm.append(time.monotonic()-start)
        finally:
            # Only the exact Popen child created above is terminated, after
            # health checks. No game/production broker/process lookup is used.
            process.terminate();process.wait(timeout=5)
    saved=(folder/'broker.log').read_bytes();(HERE/'real-broker-cli.log').write_bytes(saved)
    import sqlite3
    conn=sqlite3.connect(db);assert conn.execute('SELECT COUNT(*) FROM matches').fetchone()==(0,);assert conn.execute('SELECT COUNT(*) FROM players WHERE wins+draws+losses>0').fetchone()==(0,);conn.close()
    result={'passed':True,'actual_broker_CLI':True,'actual_production_probe_function':True,'startup_attempts':attempts,'startup_seconds':time.monotonic()-begin,
      'warm_probes':3,'warm_seconds':warm,'fresh_ranking_empty':True,'port':port,'production_ports_or_DB_used':False,'game_or_GUI_launched':False}
    (HERE/'real-broker-probe-results.json').write_text(json.dumps(result,indent=2)+'\n','utf8');print(json.dumps(result))
