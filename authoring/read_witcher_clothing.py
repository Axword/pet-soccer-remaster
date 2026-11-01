# SPDX-License-Identifier: MIT
"""Read the seven hash-pinned credited MDL inputs through external SourceIO.

No texture, game installation, source model or animation is modified.
Run in background Blender with explicit local inputs and a new separate output.
"""
from pathlib import Path
import collections
import argparse
import re
import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--character', choices=['geralt', 'ciri', 'yennefer', 'triss', 'keira', 'avallach', 'zoltan'], required=True)
parser.add_argument('--workshop-root', type=Path, required=True, help='Local folder containing the seven original Workshop-ID directories')
parser.add_argument('--profile-target', type=Path, required=True, help='Read-only approved beta2 mod/rig baseline')
parser.add_argument('--sourceio', type=Path, required=True, help='External SourceIO package directory containing __init__.py')
parser.add_argument('--contract', type=Path, default=HERE / 'witcher-clothing-contract.json')
parser.add_argument('--output', type=Path, required=True, help='New private source extraction folder')
parser.add_argument('--dry-run', action='store_true', help='Read and check sources without writing NPZ or a report')
ARGS = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
CHARACTER = ARGS.character
PROFILE = json.loads(ARGS.contract.read_text())['characters'][CHARACTER]
WORK = ARGS.output.resolve()
SOURCEIO = ARGS.sourceio.resolve()
SOURCE = ARGS.workshop_root.resolve() / PROFILE['workshop_id']
MDL = PROFILE['source_model']
CURRENT = ARGS.profile_target.resolve() / PROFILE['relative']
SELECTED = set(PROFILE['materials'])
PROVENANCE = {'materials': {k: {'atlas_region': v} for k, v in PROFILE['atlas_regions'].items()}}

def require(condition, message):
    if not condition:
        raise ValueError(message)
require(not WORK.exists(), 'Output must be new')
for readonly in (ARGS.profile_target.resolve(), ARGS.workshop_root.resolve(), SOURCEIO):
    require(not WORK.is_relative_to(readonly) and (not readonly.is_relative_to(WORK)), 'Read-only input and output must be disjoint')
require(hashlib.sha256(CURRENT.read_bytes()).hexdigest() == PROFILE['beta2_sha256'], 'Expected exact beta2 rig baseline')
for key in ('atlas', 'ini'):
    require(hashlib.sha256((ARGS.profile_target / PROFILE[key + '_relative']).read_bytes()).hexdigest() == PROFILE[key + '_sha256'], 'Frozen atlas/INI differs')
for relative, digest in PROFILE['source_input_files_sha256'].items():
    require(hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest() == digest, 'Original source MDL/VVD/VTX differs: ' + relative)
JOINTS = [None, 'ValveBiped.Bip01_Pelvis', 'ValveBiped.Bip01_Spine2', 'ValveBiped.Bip01_Neck1', 'ValveBiped.Bip01_Head1', 'ValveBiped.Bip01_L_Clavicle', 'ValveBiped.Bip01_L_UpperArm', 'ValveBiped.Bip01_L_Forearm', 'ValveBiped.Bip01_L_Hand', 'ValveBiped.Bip01_R_Clavicle', 'ValveBiped.Bip01_R_UpperArm', 'ValveBiped.Bip01_R_Forearm', 'ValveBiped.Bip01_R_Hand', 'ValveBiped.Bip01_L_Thigh', 'ValveBiped.Bip01_L_Calf', 'ValveBiped.Bip01_L_Foot', 'ValveBiped.Bip01_R_Thigh', 'ValveBiped.Bip01_R_Calf', 'ValveBiped.Bip01_R_Foot']
LABELS = ['Root', 'Pelvis', 'Spine', 'Neck', 'Head', 'LClav', 'LArm', 'LFore', 'LHand', 'RClav', 'RArm', 'RFore', 'RHand', 'LThigh', 'LCalf', 'LFoot', 'RThigh', 'RCalf', 'RFoot']

def main():
    os.environ['NO_BPY'] = '1'
    spec = importlib.util.spec_from_file_location('SourceIO', SOURCEIO / '__init__.py', submodule_search_locations=[str(SOURCEIO)])
    module = importlib.util.module_from_spec(spec)
    sys.modules['SourceIO'] = module
    spec.loader.exec_module(module)
    from SourceIO.blender_bindings.models.mdl49 import import_mdl49
    from SourceIO.blender_bindings.operators.import_settings_base import ModelOptions
    from SourceIO.library.shared.content_manager import ContentManager
    from SourceIO.library.shared.content_manager.providers.loose_files import LooseFilesContentProvider
    from SourceIO.library.utils import FileBuffer, TinyPath
    cm = ContentManager()
    cm.children.clear()
    cm._cache.clear()
    cm._exists_cache.clear()
    cm._owner_cache.clear()
    cm.add_child(LooseFilesContentProvider(TinyPath(SOURCE)))
    options = ModelOptions.default()
    options.scale = 1.0
    options.import_textures = False
    options.import_animations = False
    options.import_physics = False
    options.create_flex_drivers = False
    options.bodygroup_vis_switches = False
    options.generate_wrinkle_map_node_group = False
    container = import_mdl49(TinyPath(MDL), FileBuffer(str(SOURCE / MDL)), cm, options)
    arm = container.armature
    lookup = {name: i for i, name in enumerate(JOINTS) if name}

    def group(name):
        if name in lookup:
            return lookup[name]
        bone = arm.data.bones.get(name)
        return group(bone.parent.name) if bone and bone.parent else 1
    raw = CURRENT.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROFILE['beta2_sha256'], 'Rig baseline changed while reading sources')
    u32 = lambda at: struct.unpack_from('<I', raw, at)[0]
    at, nodes = (u32(5276), [])
    for i in range(u32(8)):
        name = raw[at + 4:at + 36].split(b'\x00', 1)[0].decode('ascii')
        nodes.append(dict(index=i, name=name, at=at, kind=u32(at)))
        at += u32(at + 152)
    node_ids = {name: next((n['index'] for n in nodes if n['name'] == 'CX_' + name)) for name in LABELS}
    skin = next((n for n in nodes if n['kind'] == 2))
    at = skin['at']
    nv = u32(at + 36)
    vp = u32(at + 140)
    sp = u32(at + 148)
    pivots = collections.defaultdict(list)
    for i in range(nv):
        p = np.array(struct.unpack_from('<3f', raw, vp + i * 12))
        a, b, *v = struct.unpack_from('<HH8f', raw, sp + i * 36)
        if v[6] > 0.001:
            pivots[a].append(p - np.array(v[:3]))
        if v[7] > 0.001:
            pivots[b].append(p - np.array(v[3:6]))
    target = {k: np.median(v, axis=0) for k, v in pivots.items()}
    source_points, target_points = ([], [])
    for label, name in zip(LABELS, JOINTS):
        if name and node_ids[label] in target:
            source_points.append(list(arm.matrix_world @ arm.data.bones[name].matrix_local.translation))
            target_points.append(target[node_ids[label]])
    src = np.array(source_points)
    dest = np.array(target_points)
    affine = np.linalg.lstsq(np.column_stack((src, np.ones(len(src)))), dest, rcond=None)[0]
    error = np.linalg.norm(np.column_stack((src, np.ones(len(src)))) @ affine - dest, axis=1)
    require(max(error) < 0.002, ('Source bind pivots do not match current model', error))
    normal_matrix = np.linalg.inv(affine[:3, :].T).T
    regions = {name: row['atlas_region'] for name, row in PROVENANCE['materials'].items()}
    vertices, normals, uv, bone_ids, weights, labels = ([], [], [], [], [], [])
    all_material_stats = collections.Counter()
    source_areas = collections.Counter()
    bodygroups = []

    def interpolate(a, b, t):
        return dict(p=a['p'].lerp(b['p'], t), n=a['n'].lerp(b['n'], t), uv=a['uv'].lerp(b['uv'], t), weights={k: a['weights'].get(k, 0) * (1 - t) + b['weights'].get(k, 0) * t for k in a['weights'].keys() | b['weights'].keys()})

    def clip(poly, axis, edge, above):
        result = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            av, bv = (a['uv'][axis] - edge, b['uv'][axis] - edge)
            ia, ib = (av >= -1e-08, bv >= -1e-08) if above else (av <= 1e-08, bv <= 1e-08)
            if ia:
                result.append(a)
            if ia != ib:
                result.append(interpolate(a, b, av / (av - bv)))
        return result
    for bodygroup, objects in container.bodygroups.items():
        chosen = objects[0] if objects else None
        bodygroups.append(dict(name=bodygroup, options=[o.name if o else None for o in objects], selected=chosen.name if chosen else None))
        if chosen is None:
            continue
        me = chosen.data
        me.calc_loop_triangles()
        groupmap = {g.index: group(g.name) for g in chosen.vertex_groups}
        for triangle in me.loop_triangles:
            label = me.materials[triangle.material_index].name
            if label not in regions:
                matches = [name for name in regions if re.sub('\\.\\d+$', '', name) == re.sub('\\.\\d+$', '', label)]
                require(len(matches) == 1, ('Ambiguous source material alias', label, matches))
                label = matches[0]
            all_material_stats[label] += 1
            if label not in SELECTED:
                continue
            ox, oy, tw, th = regions[label]
            poly = []
            for li in triangle.loops:
                vertex = me.vertices[me.loops[li].vertex_index]
                position = chosen.matrix_world @ vertex.co
                normal = (chosen.matrix_world.to_3x3() @ vertex.normal).normalized()
                ww = collections.defaultdict(float)
                for g in vertex.groups:
                    if g.weight > 0:
                        ww[groupmap[g.group]] += g.weight
                if not sum(ww.values()):
                    ww[1] = 1
                poly.append(dict(p=position, n=normal, uv=me.uv_layers[0].data[li].uv.copy(), weights=dict(ww)))
            points = np.array([np.append(np.array(v['p']), 1) @ affine for v in poly])
            source_areas[label] += float(np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0])) * 0.5)
            lo = [math.floor(min((v['uv'][k] for v in poly))) for k in range(2)]
            hi = [max(lo[k], math.ceil(max((v['uv'][k] for v in poly))) - 1) for k in range(2)]
            for tu in range(lo[0], hi[0] + 1):
                for tv in range(lo[1], hi[1] + 1):
                    piece = poly
                    for axis, edge, above in [(0, tu, True), (0, tu + 1, False), (1, tv, True), (1, tv + 1, False)]:
                        piece = clip(piece, axis, edge, above) if piece else []
                    for corner in range(1, len(piece) - 1):
                        tri = [piece[0], piece[corner], piece[corner + 1]]
                        if (tri[1]['p'] - tri[0]['p']).cross(tri[2]['p'] - tri[0]['p']).length < 1e-10:
                            continue
                        labels.append(label)
                        for v in tri:
                            p = np.append(np.array(v['p']), 1) @ affine
                            n = normal_matrix @ np.array(v['n'])
                            n /= np.linalg.norm(n)
                            u = min(1, max(0, v['uv'].x - tu))
                            vv = min(1, max(0, v['uv'].y - tv))
                            ww = sorted(v['weights'].items(), key=lambda pair: pair[1], reverse=True)[:2]
                            total = sum((w for k, w in ww))
                            ww = [(k, w / total) for k, w in ww]
                            if len(ww) == 1:
                                ww.append((ww[0][0], 0.0))
                            vertices.append(p)
                            normals.append(n)
                            uv.append(((ox + u * tw) / 2048, (oy + (1 - vv) * th) / 2048))
                            bone_ids.append([node_ids[LABELS[k]] for k, w in ww])
                            weights.append([w for k, w in ww])
    cosmetic = {'source_material_triangles': PROFILE['source_material_triangles'], 'output_material_triangles': PROFILE['current_material_triangles']}
    expected_source = {name: cosmetic['source_material_triangles'][name] for name in SELECTED}
    expected_current = {name: cosmetic['output_material_triangles'][name] for name in SELECTED}
    require(dict(collections.Counter(labels)) == expected_source, ('Source triangle totals changed', collections.Counter(labels), expected_source))
    tri = np.array(vertices).reshape(-1, 3, 3)
    areas = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1) * 0.5
    clipped_areas = {name: float(areas[np.array(labels) == name].sum()) for name in SELECTED}
    require(all((abs(clipped_areas[name] / source_areas[name] - 1) < 0.0001 for name in SELECTED)), 'Recipe invariant failed')
    source_files = {str(path.relative_to(SOURCE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [SOURCE / MDL, (SOURCE / MDL).with_suffix('.vvd'), (SOURCE / MDL).with_suffix('.dx90.vtx')]}
    require({name.replace('\\', '/'): digest for name, digest in source_files.items()} == PROFILE['source_input_files_sha256'], 'Original source changed while computing geometry')
    report = dict(character=CHARACTER, source_input_files_sha256=source_files, expected_current_selected_counts=expected_current, expected_source_selected_counts=expected_source, original_unsplit_surface_areas=dict(source_areas), repeat_split_surface_areas=clipped_areas, source_mdl=str(SOURCE / MDL), source_sha256=hashlib.sha256((SOURCE / MDL).read_bytes()).hexdigest(), current_model_sha256=hashlib.sha256(raw).hexdigest(), bodygroups=bodygroups, source_default_triangles_by_material=dict(all_material_stats), restored_original_triangles_after_repeat_UV_split=dict(collections.Counter(labels)), bind_affine=affine.tolist(), max_bind_pivot_fit_error=float(max(error)), selected_parts=sorted(SELECTED), source_and_textures_modified=False)
    if not ARGS.dry_run:
        # Every source/geometry check above must pass before creating output.
        require(not WORK.exists(), 'Output appeared while computing sources; refuse to overwrite')
        WORK.mkdir(parents=True, exist_ok=False)
        np.savez(WORK / 'authentic-clothing.npz', positions=np.array(vertices), normals=np.array(normals), uv=np.array(uv), bones=np.array(bone_ids), weights=np.array(weights), labels=np.array(labels), node_pivots=np.array([target.get(i, (0, 0, 0)) for i in range(len(nodes))]))
        (WORK / 'authentic-source.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    report['source_arrays_sha256'] = {name: hashlib.sha256(np.asarray(value).tobytes()).hexdigest() for name, value in {'positions': vertices, 'normals': normals, 'uv': uv, 'bones': bone_ids, 'weights': weights, 'labels': labels, 'node_pivots': np.array([target.get(i, (0, 0, 0)) for i in range(len(nodes))])}.items()}
    report['dry_run'] = ARGS.dry_run
    print('AUTHENTIC_CLOTHING', json.dumps(report), flush=True)
if __name__ == '__main__':
    main()
