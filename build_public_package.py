"""Create an inspectable mod-only payload, never package original game files.

Example:
python build_public_package.py --base-game "C:/Games/Pet Soccer" \
  --mod-profile "private-build/package" --output package

--mod-profile is the reviewed private build directory containing payload.tsv and
payload/. Complete modified stock files are converted to verified binary deltas.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import delta


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    values = []
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        digest, relative = line.split('\t', 1)
        parts = Path(relative)
        if len(digest) != 64 or parts.is_absolute() or '..' in parts.parts or ':' in relative:
            raise ValueError('Invalid input manifest')
        values.append((digest, relative.replace('\\', '/')))
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-game', type=Path, required=True)
    parser.add_argument('--mod-profile', type=Path, required=True)
    parser.add_argument('--base-manifest', type=Path, default=Path(__file__).parent / 'metadata/base-allowlist.tsv')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'package')
    parser.add_argument('--zip-helper-class', type=Path, default=Path(__file__).parent / 'installer/GMWZipNormalize.class')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new or empty; refuse stale complete game files')
    original = {relative.lower(): (digest, relative) for digest, relative in rows(args.base_manifest)}
    private = rows(args.mod_profile / 'payload.tsv')
    payload = output / 'payload'
    payload.mkdir(parents=True, exist_ok=True)
    standalone, patches, omitted = [], [], []
    for target_hash, relative in private:
        source = (args.mod_profile / 'payload' / relative).resolve()
        if not source.is_relative_to((args.mod_profile / 'payload').resolve()) or sha(source) != target_hash:
            raise ValueError('Private build file hash/path mismatch: ' + relative)
        if relative.lower() in original:
            base_hash, base_relative = original[relative.lower()]
            base = args.base_game / base_relative
            if sha(base) != base_hash:
                raise ValueError('Unsupported original game file: ' + base_relative)
            if base_hash == target_hash:
                omitted.append({'relative': relative, 'sha256': base_hash, 'reason': 'unchanged original, read locally'})
                continue
            base_data, target_data = base.read_bytes(), source.read_bytes()
            original_target_hash = target_hash
            if relative.lower() == 'code.pak':
                base_data, target_data = delta.normalize_zip(base_data), delta.normalize_zip(target_data)
                target_hash = hashlib.sha256(target_data).hexdigest()
            stream, metrics = delta.encode(base_data, target_data)
            if delta.apply(base_data, stream) != target_data:
                raise ValueError('Independent delta reconstruction failed')
            delta_relative = '.gmw-deltas/' + relative + '.gmwd'
            dest = payload / delta_relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(stream)
            patches.append({'relative': relative, 'base_sha256': base_hash, 'sha256': target_hash,
                            'delta_relative': delta_relative, 'delta_sha256': sha(dest),
                            'target_bytes': len(target_data), 'original_profile_sha256': original_target_hash,
                            'normalized_base_sha256': hashlib.sha256(base_data).hexdigest(), **metrics})
        else:
            if relative.lower().startswith('jre/') or relative.lower() in {'petsoccer.exe', 'chromeengine.dll', 'kernelgl.dll'}:
                raise ValueError('Original runtime must never be bundled')
            dest = payload / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            if relative.lower() == 'czytaj-gmw.txt':
                text = dest.read_text(encoding='utf-8-sig').replace('Paczka prywatna.',
                    'Wersja beta 0.1.0-beta.1. Kod moda: https://github.com/Axword/pet-soccer-remaster .')
                dest.write_text(text, encoding='utf-8-sig', newline='')
            standalone.append({'relative': relative, 'sha256': sha(dest), 'bytes': dest.stat().st_size})
    standalone.sort(key=lambda value: value['relative'].lower())
    patches.sort(key=lambda value: value['relative'].lower())
    output.mkdir(exist_ok=True)
    (output / 'payload.tsv').write_text(''.join(row['sha256'] + '\t' + row['relative'] + '\n' for row in standalone), encoding='utf8', newline='')
    (output / 'patches.tsv').write_text(''.join('\t'.join([row['base_sha256'], row['sha256'], row['delta_sha256'], row['relative'], row['delta_relative']]) + '\n' for row in patches), encoding='utf8', newline='')
    helper = payload / '.gmw-tools/GMWZipNormalize.class'
    helper.parent.mkdir(parents=True, exist_ok=True)
    if sha(args.zip_helper_class) != '100bc5030aba432464cd12ec97ab5f3b78b88da8bac23cd5b4299e60587120b0':
        raise ValueError('Rebuild helper hash contract before using a different class')
    shutil.copyfile(args.zip_helper_class, helper)
    report = {'format': 'GMWDLT1', 'standalone': standalone, 'patches': patches, 'omitted_unchanged_originals': omitted,
              'standalone_files': len(standalone), 'delta_files': len(patches),
              'bytes': sum(row['bytes'] for row in standalone) + sum(row['delta_bytes'] for row in patches),
              'no_complete_stock_files_bundled': True, 'no_game_engine_or_JRE_bundled': True,
              'base_manifest_sha256': sha(args.base_manifest), 'payload_manifest_sha256': sha(output / 'payload.tsv'),
              'patch_manifest_sha256': sha(output / 'patches.tsv'),
              'zip_normalizer_sha256': sha(helper), 'zip_normalizer_bytes': helper.stat().st_size}
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({key: value for key, value in report.items() if key not in {'standalone', 'patches', 'omitted_unchanged_originals'}}))


if __name__ == '__main__':
    main()
