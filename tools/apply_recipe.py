"""Apply one explicit bytecode recipe to a new isolated PAK, never a live game."""
from pathlib import Path
import argparse, importlib, json, sys, zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RECIPES = ['dead_diagnostics', 'attacker_status', 'console_guard', 'commentary', 'physics', 'timing', 'bracket', 'gmw_profile']

def read(path):
    with zipfile.ZipFile(path) as z: return {n:z.read(n) for n in z.namelist()}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('recipe', choices=RECIPES)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline', type=Path, help='Unpatched reference for this specific recipe stage')
    p.add_argument('--compiled', type=Path, default=ROOT/'build/java')
    p.add_argument('--snapshot', type=Path, default=ROOT/'data/profile-reference-tables.json')
    a = p.parse_args()
    if a.output.exists() or a.output.resolve() == a.input.resolve(): p.error('Use a new output file')
    classes = read(a.input)
    module = importlib.import_module('src.patches.'+a.recipe)
    kwargs = {}
    if a.recipe in ['bracket', 'gmw_profile']:
        if not a.baseline: p.error('This recipe requires its exact --baseline reference')
        kwargs = {'baseline_classes':read(a.baseline), 'compiled_dir':a.compiled}
    if a.recipe == 'gmw_profile': kwargs['snapshot'] = json.loads(a.snapshot.read_text(encoding='utf8'))
    updates = module.apply(classes, **kwargs)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.input) as before, zipfile.ZipFile(a.output, 'w') as after:
        for row in before.infolist(): after.writestr(row, updates.get(row.filename, before.read(row)))
        for name in sorted(set(updates)-set(classes)): after.writestr(name, updates[name])
    print(json.dumps({'recipe':a.recipe, 'changed_classes':sorted(updates), 'output':str(a.output)}))

if __name__ == '__main__': main()
