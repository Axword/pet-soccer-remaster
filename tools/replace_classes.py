"""Write an isolated modified PAK using compiled original mod classes."""
from pathlib import Path
import argparse, zipfile

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--classes', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.resolve() == a.input.resolve() or a.output.exists():
        p.error('Use a new output PAK, distinct from the input')
    updates = {f.relative_to(a.classes).as_posix(): f.read_bytes() for f in a.classes.rglob('*.class')}
    if not updates: p.error('No compiled classes found')
    for name, data in updates.items():
        if data[:4] != b'\xca\xfe\xba\xbe': p.error('Invalid class '+name)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.input) as before, zipfile.ZipFile(a.output, 'w') as after:
        existing = set(before.namelist())
        for row in before.infolist(): after.writestr(row, updates.get(row.filename, before.read(row)))
        for name in sorted(set(updates)-existing): after.writestr(name, updates[name])
    print('Wrote', len(updates), 'mod class replacements to', a.output)

if __name__ == '__main__': main()
