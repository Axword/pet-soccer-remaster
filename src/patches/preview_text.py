"""Patch only two menu methods, preserving all preview/facing code in the input.

The replacement GETFIELD -> INVOKESTATIC instructions have identical width and
stack effect. Branch offsets, exception tables, line maps and method sizes stay
exact. Helper source is owned. No input archive or game directory is modified.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import zipfile

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parents[1]
sys.path.insert(0, str(PUBLIC))
from tools.classfile import ClassFile, op

HELPER = 'CXPreviewText.class'
EXPECTED = {
    ('MenuChooseTeam.class', 'ShowInfo', '(I)V'): 'b2d4663b9e2045290b04de0c1abf24f6123f9cce26b82be3864657723e4965e7',
    ('MenuChooseTeamColors.class', 'SetInfo', '(LTeamData;I)V'): '076b66865ff0136e1aa1da257d764557857c66d0097054f96a6775b0ca51dc33',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def method_body(cls, name, desc):
    raw = cls.code(name, desc)[1]
    count = struct.unpack_from('>I', raw, 4)[0]
    return raw, raw[8:8 + count]


def apply(entries, helper):
    require(HELPER not in entries, 'Already patched; use the unmodified presentation input')
    require(helper[:4] == b'\xca\xfe\xba\xbe' and struct.unpack_from('>H', helper, 6)[0] == 47,
            'Helper must target the original Java 1.3 runtime')
    updates, changes = {}, []
    for (filename, method, desc), digest in EXPECTED.items():
        cls = ClassFile(entries[filename])
        original = ClassFile(entries[filename])
        raw, before = method_body(cls, method, desc)
        require(sha(before) == digest, 'Unexpected input method: ' + filename + '.' + method)
        after = before
        fields = [('m_sName', 'Name')]
        if filename == 'MenuChooseTeam.class':
            fields.append(('m_sInfo', 'Description'))
        callsites = []
        for field, function in fields:
            get_field = op(180, cls.member('TeamData', field, 'Ljava/lang/String;', 9))
            call = op(184, cls.member('CXPreviewText', function, '(LTeamData;)Ljava/lang/String;', 10))
            require(after.count(get_field) == 1, 'Expected a unique guarded field read: ' + field)
            offset = after.index(get_field)
            after = after.replace(get_field, call)
            callsites.append(dict(offset=offset, original=get_field.hex(), replacement=call.hex(),
                                  field=field, helper_function=function))
        require(len(after) == len(before), 'Method size must not change')
        cls.code(method, desc)[1] = raw[:8] + after + raw[8 + len(before):]
        for member in original.methods:
            other_name, other_desc = original.ref(member[1]), original.ref(member[2])
            if (other_name, other_desc) != (method, desc):
                require(next(m for m in cls.methods if cls.ref(m[1]) == other_name and cls.ref(m[2]) == other_desc) == member,
                        'Unrelated method changed: ' + other_name)
        require(cls.fields == original.fields and cls.bodyhead == original.bodyhead
                and cls.interfaces == original.interfaces and cls.attrs == original.attrs,
                'Class metadata outside selected method changed')
        updates[filename] = cls.emit()
        changes.append(dict(filename=filename, method=method, descriptor=desc, before_sha256=digest,
                            after_sha256=sha(after), callsites=callsites, method_bytes=len(before),
                            stack_locals_exception_debug_tables_preserved=True))
    updates[HELPER] = helper
    return updates, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--code-index', type=Path, required=True)
    parser.add_argument('--helper', type=Path, default=PUBLIC / 'build/java/CXPreviewText.class')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Output must be new')
    with zipfile.ZipFile(args.code) as source:
        infos = source.infolist()
        entries = {i.filename: source.read(i) for i in infos}
    require(len(entries) == len(infos), 'Duplicate input code entries')
    updates, changes = apply(entries, args.helper.read_bytes())
    args.output.mkdir(parents=True)
    with zipfile.ZipFile(args.output / 'code.pak', 'w') as target:
        for info in infos:
            target.writestr(info, updates.get(info.filename, entries[info.filename]))
        info = zipfile.ZipInfo(HELPER, (2000, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        target.writestr(info, updates[HELPER])
    index = args.code_index.read_bytes()
    require(HELPER.encode('ascii') not in index.splitlines(), 'Helper already indexed')
    (args.output / 'code_inf.pak').write_bytes(index.rstrip(b'\r\n') + b'\r\n' + HELPER.encode('ascii') + b'\r\n')
    classes = args.output / 'classes'
    classes.mkdir()
    for name, data in updates.items():
        (classes / name).write_bytes(data)
    with zipfile.ZipFile(args.output / 'code.pak') as result:
        require(all(result.read(n) == data for n, data in entries.items() if n not in updates),
                'Unrelated archive entry changed')
        names = result.namelist()
        require(set((args.output / 'code_inf.pak').read_text(encoding='ascii').splitlines())
                == {n for n in names if n.endswith('.class')}, 'Code index differs from class list')
    receipt = dict(input_code_sha256=sha(args.code.read_bytes()), output_code_sha256=sha((args.output / 'code.pak').read_bytes()),
                   output_index_sha256=sha((args.output / 'code_inf.pak').read_bytes()),
                   changed_classes={name: sha(data) for name, data in updates.items()}, methods=changes,
                   code_zip_entries=len(names), code_class_entries=len([n for n in names if n.endswith('.class')]),
                   preview_facing_or_canonical_TeamData_changed=False, unrelated_entries_byte_identical=True,
                   runtime_visual_test_required=True)
    (args.output / 'manifest.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'methods'}, indent=2))


if __name__ == '__main__':
    main()
