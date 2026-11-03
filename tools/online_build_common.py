"""Shared staging guards for the owned Online developer tools; no import I/O."""
from pathlib import Path
import hashlib,json,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'src/online'
DEFAULT_WORKSPACE=ROOT/'build/online'

def sha(data):return hashlib.sha256(data).hexdigest()

def workspace_path(value,require=True):
    path=Path(value).resolve();build=(ROOT/'build').resolve()
    if not build.is_relative_to(ROOT.resolve()):
        raise ValueError('The ignored build directory must resolve inside this checkout')
    if path==build or not path.is_relative_to(build):
        raise ValueError('Workspace must be a dedicated directory inside this checkout\'s ignored build/')
    marker=path/'WORKSPACE.json'
    if require:
        record=json.loads(marker.read_text('utf8'))
        if record.get('format')!='PET-SOCCER-ONLINE-SOURCE-WORKSPACE-1':raise ValueError('Not an Online source workspace')
    return path

def stage_runtime(workspace,archive=None,runtime_dir=None):
    """Verify all official bytes before writing a fresh private runtime directory."""
    workspace=workspace_path(workspace)
    if bool(archive)==bool(runtime_dir):raise ValueError('Choose exactly one --archive or --runtime-dir')
    contract=json.loads((SOURCE/'runtime-contract.json').read_text('utf8'))
    expected={row['path']:row for row in contract['files']}
    output=workspace/'payload/online/runtime'
    if output.exists():raise ValueError('Runtime output already exists; prepare a fresh workspace')
    files={}
    if archive:
        archive=Path(archive).resolve();raw=archive.read_bytes()
        if sha(raw)!=contract['archive_sha256']:raise ValueError('Official runtime archive SHA256 mismatch')
        with zipfile.ZipFile(archive) as z:
            infos=[info for info in z.infolist() if not info.is_dir()]
            if len(infos)!=len(expected) or {info.filename for info in infos}!=set(expected):
                raise ValueError('Unexpected runtime archive inventory')
            files={info.filename:z.read(info) for info in infos}
    else:
        runtime_dir=Path(runtime_dir).resolve()
        paths=list(runtime_dir.rglob('*'))
        if any(path.is_symlink() for path in paths):raise ValueError('Runtime inputs must not be symlinks')
        files={path.relative_to(runtime_dir).as_posix():path.read_bytes() for path in paths if path.is_file()}
        if set(files)!=set(expected):raise ValueError('Runtime directory does not match the full official inventory')
    for name,data in files.items():
        row=expected[name]
        if len(data)!=row['bytes'] or sha(data)!=row['sha256']:raise ValueError('Runtime byte mismatch: '+name)
        # Current official embed files are flat; validate names before any write.
        if Path(name).name!=name or '/' in name or '\\' in name or ':' in name:raise ValueError('Unsafe runtime name')
    output.mkdir(parents=True)
    for name,data in files.items():(output/name).write_bytes(data)
    report={'version':contract['version'],'architecture':contract['architecture'],
        'archive_sha256':contract['archive_sha256'],'verified_files':len(files),'license_included':'LICENSE.txt' in files}
    (workspace/'runtime-verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode('utf8'))
    return report
