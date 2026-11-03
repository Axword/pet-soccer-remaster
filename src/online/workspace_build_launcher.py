"""Build only owned portable launcher/inert probes with an external MSVC toolchain."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent

def require_workspace():
    if not (HERE/"WORKSPACE.json").is_file():
        raise SystemExit("Use tools/prepare_online_workspace.py and tools/build_online_launcher.py first; no outputs belong in src.")

def find_vcvars():
    where=Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    install=subprocess.check_output([str(where),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True,creationflags=subprocess.CREATE_NO_WINDOW).strip()
    path=Path(install)/'VC/Auxiliary/Build/vcvars32.bat'
    if not path.is_file():raise RuntimeError('Install MSVC x86 Desktop C++ build tools or pass --vcvars.')
    return path
def compile_cpp(source,output,console=False,vcvars=None):
    require_workspace()
    source=Path(source).resolve();output=Path(output).resolve()
    assert output.is_relative_to(HERE),'Build output must remain in this feature directory'
    output.parent.mkdir(parents=True,exist_ok=True)
    aux=HERE/'build'/output.stem;aux.mkdir(parents=True,exist_ok=True)
    cmd=['cl','/nologo','/utf-8','/std:c++17','/EHsc','/W4','/O2','/MT',str(source),'/Fo'+str(aux/(output.stem+'.obj')),
         '/link','/SUBSYSTEM:'+('CONSOLE' if console else 'WINDOWS'),'/OUT:'+str(output),'ws2_32.lib','user32.lib']
    batch=aux/'build.cmd'
    batch.write_text('@echo off\ncall "'+str(vcvars or find_vcvars()).replace('%','%%')+'" >nul\nif errorlevel 1 exit /b1\n'+subprocess.list2cmdline(cmd).replace('%','%%')+'\nexit /b %errorlevel%\n','utf8')
    result=subprocess.run(['cmd.exe','/d','/c',str(batch)],cwd=output.parent,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    (aux/'build.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('cp1250','replace'))
    return output
def main():
    require_workspace()
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=HERE/'payload/PetSoccer-Online.exe');p.add_argument('--vcvars',type=Path);args=p.parse_args()
    out=compile_cpp(HERE/'src/online_launcher.cpp',args.output,vcvars=args.vcvars)
    receipt={'version':'0.2.0-beta.1','wire':'GMWL-6fbcaedb-online5','required_capabilities':7,'source_sha256':hashlib.sha256((HERE/'src/online_launcher.cpp').read_bytes()).hexdigest(),
       'binary_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'binary_bytes':out.stat().st_size,'game_launched':False}
    (HERE/'launcher-build.json').write_text(json.dumps(receipt,indent=2)+'\n','utf8');print(json.dumps(receipt))
if __name__=='__main__':main()
