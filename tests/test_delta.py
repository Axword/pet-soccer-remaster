"""Executable copy/literal codec and native installer delta safety checks."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import delta


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--helper', type=Path, default=ROOT / 'installer/GMWInstallerHelper.exe')
    parser.add_argument('--output', type=Path, default=ROOT / 'tests/results.json')
    args = parser.parse_args()
    cases = []
    rng = random.Random(297)
    for index in range(100):
        base = rng.randbytes(4096 + index * 11)
        target = base[:index] + rng.randbytes(index + 3) + base[index + 11:]
        encoded, metrics = delta.encode(base, target)
        assert delta.apply(base, encoded) == target
        try:
            delta.apply(base + b'x', encoded)
        except ValueError:
            pass
        else:
            raise AssertionError('Wrong base was accepted')
    cases.append({'case': '100_deterministic_codec_roundtrips_and_wrong_base_refusals', 'passed': True})
    fixtures = ROOT / 'tests/fixtures'
    fixtures.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=fixtures, prefix='delta-') as temporary:
        root = Path(temporary)
        source, payload = root / 'source', root / 'payload'
        source.mkdir(); (payload / '.gmw-deltas').mkdir(parents=True)
        base = bytes(range(256)) * 40
        target = base[:720] + b'custom remaster class data' + base[740:] + b'END'
        stream, _ = delta.encode(base, target)
        (source / 'fixture.bin').write_bytes(base)
        (payload / 'mod.ini').write_bytes(b'[Mod]\nEnabled=1\n')
        (root / 'base.tsv').write_text(digest(base) + '\tfixture.bin\n', encoding='utf8')
        (root / 'payload.tsv').write_text(digest((payload / 'mod.ini').read_bytes()) + '\tmod.ini\n', encoding='utf8')

        def run_case(name, candidate, expected=False, rows=None, direct=False):
            (payload / '.gmw-deltas/code.pak.gmwd').write_bytes(candidate)
            row = '\t'.join([digest(base), digest(target), digest(candidate), 'fixture.bin', '.gmw-deltas/code.pak.gmwd']) + '\n'
            (root / 'patches.tsv').write_text(rows if rows is not None else row, encoding='utf8')
            dest = root / name
            result = subprocess.run([str(args.helper), 'install', str(source), str(dest), str(payload),
                                     str(root / 'base.tsv'), str(root / 'payload.tsv'), str(root / 'patches.tsv')],
                                    capture_output=True, timeout=30)
            output = (result.stdout + result.stderr).decode('utf8', 'replace').strip()
            assert (result.returncode == 0) == expected, (name, result.returncode, output)
            if expected:
                assert (dest / 'fixture.bin').read_bytes() == target
                assert not (dest / '.gmw-deltas').exists()
                removed = subprocess.run([str(args.helper), 'uninstall', str(dest)], capture_output=True, timeout=30)
                assert removed.returncode == 0
                assert not list(dest.rglob('*'))
                dest.rmdir()
            else:
                assert not dest.exists(), (name, 'failed installation was committed')
                assert not list(root.glob('.' + name + '.gmw-staging-*')), (name, 'staging not rolled back')
            assert (source / 'fixture.bin').read_bytes() == base
            cases.append({'case': name, 'passed': True, 'output': output})

        run_case('native_roundtrip', stream, True)
        run_case('bad_magic', b'INVALID!' + stream[8:])
        run_case('truncated_stream', stream[:-1])
        run_case('trailing_data', stream + b'junk')
        huge = bytearray(stream); struct.pack_into('<Q', huge, 16, 2 ** 40)
        run_case('oversized_target', bytes(huge))
        copy = stream[:88] + b'\x00' + struct.pack('<QQ', len(base) + 1, len(target)) + b'\xff'
        run_case('copy_outside_base', copy)
        zero = stream[:88] + b'\x01' + struct.pack('<Q', 0) + b'\xff'
        run_case('zero_length_command', zero)
        run_case('unknown_command', stream[:88] + b'\x03' + b'\xff')
        wrong_output = stream[:88] + b'\x01' + struct.pack('<Q', len(target)) + b'x' * len(target) + b'\xff'
        run_case('wrong_reconstructed_hash', wrong_output)
        normal_row = '\t'.join([digest(base), digest(target), digest(stream), 'fixture.bin', '.gmw-deltas/code.pak.gmwd']) + '\n'
        run_case('duplicate_patch_destination', stream, rows=normal_row + normal_row)
        run_case('traversal_destination', stream, rows=normal_row.replace('\tfixture.bin\t', '\t../code.pak\t'))
        run_case('delta_outside_dedicated_folder', stream, rows=normal_row.replace('.gmw-deltas/code.pak.gmwd', 'mod.ini'))
        run_case('wrong_original_hash', stream, rows=normal_row.replace(digest(base), '0' * 64, 1))
    report = {'backend_sha256': digest(args.helper.read_bytes()), 'checks': len(cases), 'cases': cases,
              'all_passed': True, 'game_or_UI_started': False}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps({key: value for key, value in report.items() if key != 'cases'}))


if __name__ == '__main__':
    main()
