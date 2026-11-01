# SPDX-License-Identifier: MIT
"""Restore authentic MDL clothing surfaces into the exact current 3DA rig.

Only the audited per-character clothing materials are restored. Existing animation data, texture,
other model parts and all non-skin nodes are retained. Output is a new candidate.
"""
from pathlib import Path
import collections
import argparse
import sys
import hashlib
import json
import struct
import numpy as np
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--character', choices=['geralt', 'ciri', 'yennefer', 'triss', 'keira', 'avallach', 'zoltan'], required=True)
parser.add_argument('--profile-target', type=Path, required=True, help='Read-only approved beta2 mod/rig baseline')
parser.add_argument('--source-extract', type=Path, required=True, help='Private NPZ/report produced by read_witcher_clothing.py')
parser.add_argument('--output', type=Path, required=True, help='New isolated repaired mesh output')
parser.add_argument('--contract', type=Path, default=HERE / 'witcher-clothing-contract.json')
parser.add_argument('--allow-render-bounds-expansion', action='store_true')
parser.add_argument('--dry-run', action='store_true', help='Compute and validate the expected output without writing a mesh')
ARGS = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
CHARACTER = ARGS.character
PROFILE = json.loads(ARGS.contract.read_text())['characters'][CHARACTER]
SOURCE_INFO = json.loads((ARGS.source_extract / 'authentic-source.json').read_text())
CURRENT = ARGS.profile_target.resolve() / PROFILE['relative']
PROVENANCE_DATA = {'materials': {k: {'atlas_region': v} for k, v in PROFILE['atlas_regions'].items()}}
EXPECTED = PROFILE['beta2_sha256']
PARTS = set(PROFILE['materials'])
HIDDEN=set(PROFILE.get('omit_optional_materials',{}))

def require(condition, message):
    if not condition:
        raise ValueError(message)
require(not ARGS.output.exists(), 'Output must be new')
require(PARTS == set(SOURCE_INFO['selected_parts']), 'Extracted material set differs')
require(not HIDDEN or (CHARACTER=='avallach' and HIDDEN=={'mask'}),'Only the prescribed authentic optional mask bodygroup may be omitted')
if HIDDEN:
    choices=[row for row in SOURCE_INFO['bodygroups'] if row['name']=='mask']
    require(len(choices)==1 and None in choices[0]['options'],'Original source does not expose the requested empty mask bodygroup')
require(SOURCE_INFO['current_model_sha256'] == EXPECTED, 'Extracted rig baseline differs')
for readonly in (ARGS.profile_target.resolve(), ARGS.source_extract.resolve()):
    require(not ARGS.output.resolve().is_relative_to(readonly) and (not readonly.is_relative_to(ARGS.output.resolve())), 'Read-only input and output must be disjoint')
for key in ('atlas', 'ini'):
    require(hashlib.sha256((ARGS.profile_target / PROFILE[key + '_relative']).read_bytes()).hexdigest() == PROFILE[key + '_sha256'], 'Frozen atlas/INI differs')

def sha(value):
    return hashlib.sha256(value).hexdigest()

def main():
    target = ARGS.output / ('Data/Meshes/Animals/cx_w3_' + CHARACTER + '.3da')
    require(not target.exists(), 'Recipe invariant failed')
    raw = CURRENT.read_bytes()
    require(sha(raw) == EXPECTED, 'Recipe invariant failed')
    u32 = lambda at: struct.unpack_from('<I', raw, at)[0]
    nodes, at = ([], u32(5276))
    for _ in range(u32(8)):
        node = dict(base=at, kind=u32(at), size=u32(at + 152), nv=u32(at + 36), nf=u32(at + 40), p=[u32(at + j) for j in range(108, 152, 4)])
        nodes.append(node)
        at += node['size']
    skin = nodes[-1]
    require(skin['kind'] == 2 and sum((n['kind'] == 2 for n in nodes)) == 1, 'Recipe invariant failed')
    base, p, nv, nf = (skin['base'], skin['p'], skin['nv'], skin['nf'])
    regions = {name: row['atlas_region'] for name, row in PROVENANCE_DATA['materials'].items()}
    old_attributes = [raw[p[8] + i * 12:p[8] + (i + 1) * 12] + raw[p[9] + i * 12:p[9] + (i + 1) * 12] + raw[p[7] + i * 8:p[7] + (i + 1) * 8] + raw[p[10] + i * 36:p[10] + (i + 1) * 36] for i in range(nv)]
    old_faces = [struct.unpack_from('<3H', raw, p[4] + i * 6) for i in range(nf)]
    groups = struct.unpack_from('<' + 'H' * nf, raw, p[5])
    require(set(groups) == {0}, 'Recipe invariant failed')
    old_uv = np.array([struct.unpack('<2f', v[24:32]) for v in old_attributes])
    old_labels = []
    for face in old_faces:
        u, v = old_uv[list(face)].mean(axis=0) * 2048
        old_labels.append(next((name for name, (x, y, w, h) in regions.items() if x - 0.01 <= u <= x + w + 0.01 and y - 0.01 <= v <= y + h + 0.01), 'outside'))
    require({name: collections.Counter(old_labels)[name] for name in PARTS} == SOURCE_INFO['expected_current_selected_counts'], 'Recipe invariant failed')
    for name,count in PROFILE.get('omit_optional_materials',{}).items():
        require(collections.Counter(old_labels)[name]==count,'Optional source-bodygroup face count differs')
    authentic = np.load(ARGS.source_extract / 'authentic-clothing.npz')
    source_labels = authentic['labels'].tolist()
    require(dict(collections.Counter(source_labels)) == SOURCE_INFO['expected_source_selected_counts'], 'Recipe invariant failed')
    new_attributes = []
    for point, normal, uv, bones, weights in zip(authentic['positions'], authentic['normals'], authentic['uv'], authentic['bones'], authentic['weights']):
        a, b = map(int, bones)
        pa = point - authentic['node_pivots'][a]
        pb = point - authentic['node_pivots'][b]
        attr = struct.pack('<3f3f2fHH8f', *point, *normal, *uv, a, b, *pa, *pb, *weights)
        require(len(attr) == 68 and np.isfinite(np.array(struct.unpack('<8f', attr[:32]))).all(), 'Recipe invariant failed')
        new_attributes.append(attr)
    unique, lookup, indices, final_labels = ([], {}, [], [])
    old_retained = hashlib.sha256()
    new_retained = hashlib.sha256()

    def append(corners, label):
        final_labels.append(label)
        for attr in corners:
            if attr not in lookup:
                lookup[attr] = len(unique)
                unique.append(attr)
            indices.append(lookup[attr])
    for face, label in zip(old_faces, old_labels):
        if label in PARTS or label in HIDDEN:
            continue
        attrs = [old_attributes[i] for i in face]
        for attr in attrs:
            old_retained.update(attr)
        append(attrs, label)
    for fi, label in enumerate(source_labels):
        append(new_attributes[fi * 3:fi * 3 + 3], label)
    new_nv, new_nf = (len(unique), len(final_labels))
    require(max(indices) < 65536 and new_nv <= 65535, 'Recipe invariant failed')
    positions = np.array([struct.unpack('<3f', v[:12]) for v in unique])
    old_bounds = np.array(struct.unpack_from('<6f', raw, base + 80)).reshape(2, 3)
    new_bounds = np.array([np.minimum(old_bounds[0], positions.min(axis=0)), np.maximum(old_bounds[1], positions.max(axis=0))])
    policy=PROFILE['render_bounds_policy']
    if policy['mode']=='preserve_approved_within_tolerance':
        tolerance=policy['preserve_tolerance']
        require(np.all(positions>=old_bounds[0]-tolerance) and np.all(positions<=old_bounds[1]+tolerance),'Restored source exceeded approved preserved-bounds tolerance')
        new_bounds=old_bounds.copy()
    else:
        require(policy['mode']=='expand_exact_union','Unknown approved render-bound policy')
    bounds_changed = not np.array_equal(old_bounds, new_bounds)
    require(not bounds_changed or ARGS.allow_render_bounds_expansion, ('Restored source requires exact render AABB expansion', old_bounds, new_bounds))
    replacements = {4: struct.pack('<' + 'H' * len(indices), *indices), 5: bytes(new_nf * 2), 6: struct.pack('<' + 'H' * len(indices), *indices), 7: b''.join((v[24:32] for v in unique)), 8: b''.join((v[:12] for v in unique)), 9: b''.join((v[12:24] for v in unique)), 10: b''.join((v[32:] for v in unique))}
    streams = sorted(((offset, index) for index, offset in enumerate(p) if offset))
    lengths = {index: (streams[i + 1][0] if i + 1 < len(streams) else len(raw)) - offset for i, (offset, index) in enumerate(streams)}
    block = bytearray(raw[base:base + 156])
    track_proof = {}
    for offset, index in streams:
        destination = base + len(block)
        struct.pack_into('<I', block, 108 + index * 4, destination)
        payload = bytearray(replacements.get(index, raw[offset:offset + lengths[index]]))
        if index in (0, 1, 2):
            key = struct.unpack_from('<I', payload, 12)[0]
            normalized = bytes(payload[:12]) + struct.pack('<I', key - offset) + bytes(payload[16:])
            track_proof[str(index)] = sha(normalized)
            struct.pack_into('<I', payload, 12, key - offset + destination)
        block.extend(payload)
    for offset, value in ((36, new_nv), (40, new_nf), (48, new_nf), (64, new_nv), (152, len(block))):
        struct.pack_into('<I', block, offset, value)
    if bounds_changed:
        struct.pack_into('<6f', block, 80, *new_bounds.flatten())
    result = bytearray(raw[:base]) + block
    struct.pack_into('<I', result, 5268, u32(5268) + new_nf - nf)
    struct.pack_into('<I', result, 5272, u32(5272) + new_nv - nv)
    global_before = np.array(struct.unpack_from('<6f', raw, 5280)).reshape(2, 3)
    global_after = np.array([np.minimum(global_before[0], positions.min(axis=0)), np.maximum(global_before[1], positions.max(axis=0))])
    if bounds_changed:
        struct.pack_into('<6f', result, 5280, *global_after.flatten())
    else:
        global_after=global_before.copy()
    require(result[u32(5276):base] == raw[u32(5276):base], 'Recipe invariant failed')
    require(result[:5268] == raw[:5268] and result[5276:5280] == raw[5276:5280] and (result[5304:base] == raw[5304:base]), 'Recipe invariant failed')
    require(result[base:base + 36] == raw[base:base + 36] and result[base + 104:base + 108] == raw[base + 104:base + 108], 'Recipe invariant failed')
    if not bounds_changed:
        require(result[base + 80:base + 104] == raw[base + 80:base + 104] and result[5280:5304] == raw[5280:5304], 'Recipe invariant failed')
    for index in (0, 1, 2):
        offset = struct.unpack_from('<I', result, base + 108 + index * 4)[0]
        payload = result[offset:offset + lengths[index]]
        normalized = bytes(payload[:12]) + struct.pack('<I', struct.unpack_from('<I', payload, 12)[0] - offset) + bytes(payload[16:])
        require(sha(normalized) == track_proof[str(index)], 'Recipe invariant failed')
    retained_count = sum((label not in PARTS and label not in HIDDEN for label in old_labels))
    for i in indices[:retained_count * 3]:
        new_retained.update(unique[i])
    require(old_retained.hexdigest() == new_retained.hexdigest(), 'Recipe invariant failed')
    authentic_corners = hashlib.sha256(b''.join(new_attributes)).hexdigest()
    restored_corners = hashlib.sha256(b''.join((unique[i] for i in indices[retained_count * 3:]))).hexdigest()
    require(authentic_corners == restored_corners, 'Recipe invariant failed')
    require(sha(result) == PROFILE['output_sha256'] and len(result) == PROFILE['output_bytes'], 'Output differs from the reviewed deterministic recipe')
    if not ARGS.dry_run:
        target.parent.mkdir(parents=True)
        target.write_bytes(result)
    report = dict(character=CHARACTER, source_extraction=str(ARGS.source_extract), source_input_files_sha256=SOURCE_INFO['source_input_files_sha256'], source_model_sha256=sha(raw), output_sha256=sha(result), relative='Data/Meshes/Animals/cx_w3_' + CHARACTER + '.3da', source_bytes=len(raw), output_bytes=len(result), vertices_before=nv, vertices_after=new_nv, triangles_before=nf, triangles_after=new_nf, max_index=max(indices), replaced_parts=sorted(PARTS), old_material_triangles=dict(collections.Counter(old_labels)), restored_material_triangles=dict(collections.Counter(source_labels)), final_material_triangles=dict(collections.Counter(final_labels)), retained_corner_attributes_sha256=old_retained.hexdigest(), restored_source_corner_attributes_sha256=authentic_corners, non_skin_nodes_exact=True, skin_track_payloads_relative_exact=track_proof, header_bounds_exact=not bounds_changed, render_bounds_expansion=dict(changed=bounds_changed, skin_offset=base + 80, global_offset=5280, skin_before=old_bounds.tolist(), skin_after=new_bounds.tolist(), global_before=global_before.tolist(), global_after=global_after.tolist(), rule='Contract-prescribed preserved AABB within0.002 or exact expanded union; no clipping or extra margin'), skin_hierarchy_exact=True, texture_or_ini_modified=False, game_or_QA_modified=False, native_visual_acceptance=False)
    report['omitted_original_optional_bodygroup_materials']=PROFILE.get('omit_optional_materials',{})
    report['dry_run'] = ARGS.dry_run
    if not ARGS.dry_run:
        (ARGS.output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
