"""Rename only the three GMW clubs; retain historical species and all asset paths.

Import ``apply(classes)`` from the public source tree, or run this standalone
with --source-root pointing at that tree. Output must be a new archive.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import zipfile

CLUBS = (
    {"species": 37, "universe": "Minecraft", "old_name": "Minecraft", "old_abbr": "MCF",
     "name": "Borussia Blockmund", "abbr": "BBM", "short": "Blockmund",
     "genitive": "Borussii Blockmund", "parody": "Borussia Dortmund", "home": 41,
     "base_wave": "Data/Sounds/CX/Names/n_e098b8a25b0a.wav",
     "genitive_wave": "Data/Sounds/CX/Names/n_e098b8a25b0ab.wav"},
    {"species": 44, "universe": "Gothic", "old_name": "Gothic", "old_abbr": "GTH",
     "name": "Górnik Khorinis", "abbr": "GKH", "short": "Khorinis",
     "genitive": "Górnika Khorinis", "parody": "Górnik Zabrze", "home": 38,
     "base_wave": "Data/Sounds/CX/Names/n_e7dd6b4ae670.wav",
     "genitive_wave": "Data/Sounds/CX/Names/n_e7dd6b4ae670b.wav"},
    {"species": 51, "universe": "Wiedźmin", "old_name": "Wiedzmin", "old_abbr": "WCH",
     "name": "Wiedźminhampton", "abbr": "WHP", "short": "Wiedźmin",
     "genitive": "Wiedźminhampton", "parody": "Wolverhampton Wanderers", "home": 40,
     "base_wave": "Data/Sounds/CX/Names/n_b7692afb7d6a.wav",
     "genitive_wave": "Data/Sounds/CX/Names/n_b7692afb7d6ab.wav"},
)


def apply(classes):
    from tools.classfile import ClassFile, U2
    if 'CXGMWProfile.class' not in classes:
        raise AssertionError('This rename is for the GMW-only profile, not the legacy full-team Test copy')
    selector = ClassFile(classes['MenuChooseTeam.class'])
    select_raw = selector.code('<init>', '()V')[1]
    select_count = struct.unpack_from('>I', select_raw, 4)[0]
    select_body = select_raw[8:8 + select_count]
    if select_body.count(b'\x10\x0f\xbd' + U2(selector.clazz('TeamData'))) != 1:
        raise AssertionError('Expected exactly fifteen allocated selector teams')
    original = classes['ETeams.class']
    c = ClassFile(original)
    attr = c.code('InitTeamData', '()V')
    raw = attr[1]
    count = struct.unpack_from('>I', raw, 4)[0]
    body = raw[8:8 + count]

    def loads(values):
        return b''.join(b'\x13' + U2(c.string(s)) for s in values)

    for row in CLUBS:
        old = loads((row['old_name'], row['old_abbr'], row['old_name']))
        new = loads((row['name'], row['abbr'], row['short']))
        old_count, new_count = body.count(old), body.count(new)
        if old_count == 0 and new_count == 1:
            continue
        if old_count != 1 or new_count != 0:
            raise AssertionError(('Unexpected club metadata; review before editing', row['species'], old_count, new_count))
        body = body.replace(old, new)
    # All replacements are three ldc_w instructions, so code lengths, branches,
    # exception tables and nested debug attributes retain their original offsets.
    assert len(body) == count
    attr[1] = raw[:8] + body + raw[8 + count:]
    result = c.emit()
    return {} if result == original else {'ETeams.class': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path,
        default=Path(__file__).resolve().parents[2])
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.input.resolve() == args.output.resolve():
        raise ValueError('Output must be new; never overwrite an installed game archive')
    sys.path.insert(0, str(args.source_root))
    with zipfile.ZipFile(args.input) as z:
        infos = z.infolist()
        classes = {info.filename: z.read(info) for info in infos}
    updates = apply(classes)
    candidate = dict(classes, **updates)
    assert not apply(candidate), 'Rename recipe must be idempotent'
    assert all(classes[n] == candidate[n] for n in classes if n != 'ETeams.class')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w') as z:
        for info in infos:
            z.writestr(info, candidate[info.filename])
    report = {
        'input': str(args.input), 'output': str(args.output),
        'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'changed_classes': list(updates), 'all_other_entries_unchanged': True,
        'clubs': CLUBS,
        'species_map_roster_texture_and_voice_paths_unchanged': True,
        'voice_status': 'Existing accepted faction-name recordings retained; no new-name recordings exist.',
        'idempotent': True, 'game_launched': False,
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
