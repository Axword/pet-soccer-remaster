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

VERSION = '0.2.0-beta.1'
RESERVED = {'.gmw-files.tsv', '.gmw-owner.txt', 'gmwinstallerhelper.exe', 'odinstaluj.exe'}


def relative_name(value):
    if not isinstance(value, str):
        raise ValueError('Manifest paths must be strings')
    value = value.replace('\\', '/')
    parts = value.split('/')
    if (not value or any(c in value for c in '\0\t\r\n:*?"<>|')
            or any(not p or p in {'.', '..'} or p[-1] in '. ' for p in parts)):
        raise ValueError('Invalid relative manifest path: ' + repr(value))
    for part in parts:
        stem = part.split('.')[0].lower()
        if stem in {'con', 'prn', 'aux', 'nul', 'conin$', 'conout$'} or (
                len(stem) == 4 and stem[:3] in {'com', 'lpt'} and stem[3] in '123456789'):
            raise ValueError('Windows device file name: ' + value)
    return value


def target_name(value):
    value = relative_name(value)
    parts = value.lower().split('/')
    if parts[-1] in RESERVED or parts[0] in {'.gmw-deltas', '.gmw-tools'}:
        raise ValueError('Installer-reserved target: ' + value)
    return value


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    values, seen = [], set()
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        if not line:
            continue
        digest, relative = line.split('\t', 1)
        relative = relative_name(relative)
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid input manifest')
        if relative.lower() in seen:
            raise ValueError('Duplicate input manifest target: ' + relative)
        seen.add(relative.lower())
        values.append((digest, relative))
    return values


def source_mapping(path, original, private):
    if path is None:
        return {}
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            key = target_name(key).lower()
            if key in result:
                raise ValueError('Duplicate source-map target: ' + key)
            result[key] = relative_name(value)
        return result
    mapping = json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique_object)
    if not isinstance(mapping, dict):
        raise ValueError('Source map must be a JSON target-to-stock-source object')
    targets = {relative.lower() for _, relative in private}
    for target, source in mapping.items():
        if target not in targets:
            raise ValueError('Unused source-map target: ' + target)
        if source.lower() not in original:
            raise ValueError('Source-map base is not stock allowlisted: ' + source)
    return mapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-game', type=Path, required=True)
    parser.add_argument('--mod-profile', type=Path, required=True)
    parser.add_argument('--base-manifest', type=Path, default=Path(__file__).parent / 'metadata/base-allowlist.tsv')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'package')
    parser.add_argument('--zip-helper-class', type=Path, default=Path(__file__).parent / 'installer/GMWZipNormalize.class')
    parser.add_argument('--source-map', type=Path, help='JSON object mapping a mod target to its original allowlisted base path')
    args = parser.parse_args()
    output = args.output.resolve()
    for input_root in (args.base_game.resolve(), args.mod_profile.resolve()):
        if output.is_relative_to(input_root) or input_root.is_relative_to(output):
            raise ValueError('Output and original/profile inputs must be separate trees')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new or empty; refuse stale complete game files')
    original = {relative.lower(): (digest, relative) for digest, relative in rows(args.base_manifest)}
    private = rows(args.mod_profile / 'payload.tsv')
    for _, relative in private:
        target_name(relative)
    mapped = source_mapping(args.source_map, original, private)
    payload = output / 'payload'
    payload.mkdir(parents=True, exist_ok=True)
    standalone, patches, omitted = [], [], []
    for target_hash, relative in private:
        source = (args.mod_profile / 'payload' / relative).resolve()
        if not source.is_relative_to((args.mod_profile / 'payload').resolve()) or sha(source) != target_hash:
            raise ValueError('Private build file hash/path mismatch: ' + relative)
        source_key = mapped.get(relative.lower(), relative).lower()
        if source_key in original:
            base_hash, base_relative = original[source_key]
            base = (args.base_game / base_relative).resolve()
            if not base.is_relative_to(args.base_game.resolve()) or sha(base) != base_hash:
                raise ValueError('Unsupported original game file: ' + base_relative)
            alias = base_relative.lower() != relative.lower()
            if base_hash == target_hash and not alias:
                omitted.append({'relative': relative, 'sha256': base_hash, 'reason': 'unchanged original, read locally'})
                continue
            base_data, target_data = base.read_bytes(), source.read_bytes()
            original_target_hash = target_hash
            if relative.lower() == 'code.pak' or base_relative.lower() == 'code.pak':
                base_data, target_data = delta.normalize_zip(base_data), delta.normalize_zip(target_data)
                target_hash = hashlib.sha256(target_data).hexdigest()
            stream, metrics = delta.encode(base_data, target_data)
            if delta.apply(base_data, stream) != target_data:
                raise ValueError('Independent delta reconstruction failed')
            delta_relative = '.gmw-deltas/' + relative + '.gmwd'
            dest = payload / delta_relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(stream)
            patches.append({'relative': relative, 'base_relative': base_relative, 'base_sha256': base_hash, 'sha256': target_hash,
                            'delta_relative': delta_relative, 'delta_sha256': sha(dest),
                            'target_bytes': len(target_data), 'original_profile_sha256': original_target_hash,
                            'normalized_base_sha256': hashlib.sha256(base_data).hexdigest(), **metrics})
        else:
            if relative.lower().startswith('jre/') or relative.lower() in {'petsoccer.exe', 'petsoccer.bum', 'code.pak', 'code_inf.pak', 'chromeengine.dll', 'kernelgl.dll'}:
                raise ValueError('Original runtime must never be bundled')
            dest = payload / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            if relative.lower() == 'czytaj-gmw.txt':
                text = dest.read_text(encoding='utf-8-sig').replace('Paczka prywatna.',
                    'Wersja beta ' + VERSION + '. Kod moda: https://github.com/Axword/pet-soccer-remaster .')
                text = text.replace('Wersja beta 0.1.0-beta.3.', 'Wersja beta ' + VERSION + '.')
                dest.write_text(text, encoding='utf-8-sig', newline='')
            standalone.append({'relative': relative, 'sha256': sha(dest), 'bytes': dest.stat().st_size})
    standalone.sort(key=lambda value: value['relative'].lower())
    patches.sort(key=lambda value: value['relative'].lower())
    output.mkdir(exist_ok=True)
    (output / 'payload.tsv').write_text(''.join(row['sha256'] + '\t' + row['relative'] + '\n' for row in standalone), encoding='utf8', newline='')
    def patch_row(row):
        values = [row['base_sha256'], row['sha256'], row['delta_sha256'], row['relative'], row['delta_relative']]
        if row['base_relative'].lower() != row['relative'].lower():
            values.append(row['base_relative'])
        return '\t'.join(values) + '\n'
    (output / 'patches.tsv').write_text(''.join(patch_row(row) for row in patches), encoding='utf8', newline='')
    helper = payload / '.gmw-tools/GMWZipNormalize.class'
    helper.parent.mkdir(parents=True, exist_ok=True)
    if sha(args.zip_helper_class) != '100bc5030aba432464cd12ec97ab5f3b78b88da8bac23cd5b4299e60587120b0':
        raise ValueError('Rebuild helper hash contract before using a different class')
    shutil.copyfile(args.zip_helper_class, helper)
    report = {'format': 'GMWDLT1', 'standalone': standalone, 'patches': patches, 'omitted_unchanged_originals': omitted,
              'standalone_files': len(standalone), 'delta_files': len(patches),
              'bytes': sum(row['bytes'] for row in standalone) + sum(row['delta_bytes'] for row in patches),
              'no_complete_stock_files_bundled': True, 'no_game_engine_or_JRE_bundled': True,
              'alias_delta_files': sum(row['base_relative'].lower() != row['relative'].lower() for row in patches),
              'base_manifest_sha256': sha(args.base_manifest), 'payload_manifest_sha256': sha(output / 'payload.tsv'),
              'patch_manifest_sha256': sha(output / 'patches.tsv'),
              'zip_normalizer_sha256': sha(helper), 'zip_normalizer_bytes': helper.stat().st_size}
    (output / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({key: value for key, value in report.items() if key not in {'standalone', 'patches', 'omitted_unchanged_originals'}}))


if __name__ == '__main__':
    main()
