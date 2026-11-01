"""Build the x86 JNI bridge with external MSVC and JDK headers; never edit a game."""
from pathlib import Path
import argparse, os, subprocess, shutil

ROOT = Path(__file__).resolve().parents[1]

def find_vcvars():
    program_files = os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')
    vswhere = Path(program_files)/'Microsoft Visual Studio/Installer/vswhere.exe'
    if not vswhere.is_file():
        raise SystemExit('Install the MSVC x86 C++ tools, or run from an x86 Native Tools prompt.')
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*',
        '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
        text=True).strip()
    vcvars = Path(install)/'VC/Auxiliary/Build/vcvars32.bat'
    if not vcvars.is_file(): raise SystemExit('No MSVC x86 toolchain found')
    return vcvars

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jni-dir', type=Path, help='Directory containing external jni.h and optionally jni_md.h')
    parser.add_argument('--output', type=Path, default=ROOT/'build/native')
    args = parser.parse_args()
    jdk = Path(os.environ.get('JAVA_HOME', ''))
    includes = [args.jni_dir.resolve()] if args.jni_dir else [jdk/'include', jdk/'include/win32']
    if not any((d/'jni.h').is_file() for d in includes) or not any((d/'jni_md.h').is_file() for d in includes):
        parser.error('Set JAVA_HOME to an external Windows JDK, or supply --jni-dir')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    command = ['cl', '/nologo', '/utf-8', '/std:c++17', '/EHsc', '/W4', '/O2', '/MT', '/LD']
    command += ['/I'+str(d.resolve()) for d in includes]
    command += [str(ROOT/'src/native/cxsupport.cpp'), '/Fo'+str(output/'cxsupport.obj'),
                '/link', '/OUT:'+str(output/'cxsupport.dll'), 'user32.lib', 'opengl32.lib']
    if shutil.which('cl'):
        subprocess.run(command, check=True, cwd=output)
    else:
        vcvars = find_vcvars()
        # Use a build-only batch file to avoid cmd.exe's nested /c quoting rules.
        # Percent signs are escaped for batch expansion; no credentials are read.
        line = subprocess.list2cmdline(command).replace('%', '%%')
        batch = output/'build-native.cmd'
        batch.write_text('@echo off\ncall "'+str(vcvars).replace('%', '%%')+'" >nul\n'
                         'if errorlevel 1 exit /b 1\n'+line+'\nexit /b %errorlevel%\n', encoding='utf8')
        subprocess.run(['cmd.exe', '/d', '/c', batch.name], check=True, cwd=output)
    print('Built', output/'cxsupport.dll')

if __name__ == '__main__': main()
