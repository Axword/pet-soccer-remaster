# SPDX-License-Identifier: MIT
"""Reproduce the two beta3 map-normal edits from exact beta2 mod assets.

This owned recipe uses only the Python standard library. It changes selected
stored normals in two static backdrops. It never edits an installed source game,
loads an engine, changes terrain/collision, or ships any game-derived asset.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import struct


RECIPE_VERSION = 'beta3-map-normals-1'
CREASE_DEGREES = 55.0
BLEND = 0.55
RULES = {
    38: {'cx38_crag.png'},
    40: {'cx40v2_cliff.png', 'cx40v2_clifftop.png',
         'cx40v2_leaf.png', 'cx40v2_leaflit.png'},
}
INPUT_SHA256 = {
    38: 'da867fc8b33a5c092010f558e5ccb427894d05bbba6b89c49c54aec1c1e94a11',
    40: '73e1afc05c31ffad83e55a3545cb1d97bc085f012780635e3d9388a6988bbfb7',
}
OUTPUT_SHA256 = {
    38: '07841d048ab26c9b4d3c99ef0435a1a79e353d3fa404bbbb0b699f0d38fc8ddb',
    40: 'f08884fe7b511568b2120ff14da23c75559e666ff04820260cb7f6b4cbedbf6e',
}


def require(condition, message):
    """Keep validation active even when Python is invoked with -O."""
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def length(vector):
    return math.sqrt(dot(vector, vector))


def unit(vector):
    size = length(vector)
    require(math.isfinite(size) and size > 1e-9, 'Nonfinite or zero-length vector')
    return tuple(x / size for x in vector)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def angle(a, b):
    cosine = max(-1.0, min(1.0, dot(unit(a), unit(b))))
    return math.degrees(math.acos(cosine))


def parse_static_backdrop(raw):
    """Read only the supported static layout, not a general .3da importer.

    Offsets were observed in the two hash-pinned mod backdrops. Streams 8 and 9
    contain float32 positions and normals; streams 4 and 5 contain triangle
    indices and material IDs. Other sections are retained as opaque bytes.
    """
    def u32(offset):
        return struct.unpack_from('<I', raw, offset)[0]

    require(len(raw) >= 5280 and raw[:8] == b'3DA_\x01\x01\0\0', 'Unsupported static backdrop header')
    require(u32(8) == 1 and u32(12) == 1, 'Only the supported single-node static backdrops are accepted')
    names = [raw[16 + i * 164:48 + i * 164].split(b'\0', 1)[0].decode('ascii')
             for i in range(u32(5264))]
    node = u32(5276)
    require(node + 156 <= len(raw) and u32(node) == 1
            and node + u32(node + 152) == len(raw), 'Unsupported node layout')
    vertex_count, face_count = u32(node + 36), u32(node + 40)
    streams = [u32(node + offset) for offset in range(108, 152, 4)]
    for offset, count, stride in ((streams[8], vertex_count, 12), (streams[9], vertex_count, 12),
                                  (streams[4], face_count, 6), (streams[5], face_count, 2)):
        require(offset + count * stride <= len(raw), 'Stream extends outside the file')
    points = [struct.unpack_from('<3f', raw, streams[8] + i * 12) for i in range(vertex_count)]
    normals = [struct.unpack_from('<3f', raw, streams[9] + i * 12) for i in range(vertex_count)]
    faces = [struct.unpack_from('<3H', raw, streams[4] + i * 6) for i in range(face_count)]
    groups = struct.unpack_from('<' + 'H' * face_count, raw, streams[5])
    require(all(max(face) < vertex_count for face in faces), 'Invalid triangle index')
    require(all(group < len(names) for group in groups), 'Invalid material index')
    require(all(all(math.isfinite(x) for x in vector) for vector in points + normals), 'Nonfinite vertex data')
    require(all(.999 < length(normal) < 1.001 for normal in normals), 'Input normals are not unit length')
    return names, vertex_count, face_count, streams, points, normals, faces, groups


def polish_bytes(raw, map_id):
    """Return bytes and a report; no filesystem writes occur in this function."""
    require(map_id in RULES, 'Unsupported map ID')
    require(sha(raw) == INPUT_SHA256[map_id], 'Input hash differs; inspect the new baseline before editing')
    names, vertex_count, face_count, streams, points, old, faces, groups = parse_static_backdrop(raw)
    allowed = {i for i, name in enumerate(names) if name in RULES[map_id]}
    require({names[i] for i in allowed} == RULES[map_id], 'Expected material names differ')

    face_normals, areas = [], []
    vertex_faces = collections.defaultdict(set)
    edges = collections.defaultdict(list)
    for face_index, face in enumerate(faces):
        a, b, c = [points[i] for i in face]
        axis = cross(sub(b, a), sub(c, a))
        weight = length(axis)
        reference = unit(tuple(sum(old[i][k] for i in face) for k in range(3)))
        # Preserve pre-existing degenerate triangles; do not change topology.
        if weight <= 1e-7:
            face_normals.append(reference)
            areas.append(0.0)
            continue
        normal = unit(axis)
        if dot(normal, reference) < 0:
            normal = tuple(-x for x in normal)
        face_normals.append(normal)
        areas.append(weight)
        if groups[face_index] not in allowed:
            continue
        for vertex in face:
            vertex_faces[(groups[face_index], points[vertex])].add(face_index)
        for j in range(3):
            a, b = points[face[j]], points[face[(j + 1) % 3]]
            if a != b:
                edges[(groups[face_index], tuple(sorted((a, b))))].append(face_index)

    adjacency = collections.defaultdict(lambda: collections.defaultdict(set))
    threshold = math.cos(math.radians(CREASE_DEGREES))
    smooth_edges, sharp_edges = 0, 0
    for (material, (a, b)), joined in edges.items():
        joined = list(set(joined))
        # Join only a manifold shared edge of the same material. Mere point
        # coincidence, isolated surfaces and nonmanifold edges do not join.
        if len(joined) != 2:
            continue
        first, second = joined
        if dot(face_normals[first], face_normals[second]) < threshold:
            sharp_edges += 1
            continue
        smooth_edges += 1
        for point in (a, b):
            graph = adjacency[(material, point)]
            graph[first].add(second)
            graph[second].add(first)

    desired, component_count = {}, 0
    for key, incident in vertex_faces.items():
        graph, remaining = adjacency[key], set(incident)
        while remaining:
            first = remaining.pop()
            component, stack = {first}, [first]
            while stack:
                for other in graph[stack.pop()]:
                    if other in remaining:
                        remaining.remove(other)
                        component.add(other)
                        stack.append(other)
            total = tuple(sum(face_normals[i][k] * areas[i] for i in component) for k in range(3))
            if length(total) < 1e-9:
                continue
            normal = unit(total)
            component_count += 1
            for face_index in component:
                desired[(key, face_index)] = normal

    candidates, owners = collections.defaultdict(list), collections.defaultdict(set)
    for face_index, face in enumerate(faces):
        for vertex in face:
            owners[vertex].add(groups[face_index])
            if groups[face_index] in allowed and areas[face_index] > 0:
                candidates[vertex].append(desired[((groups[face_index], points[vertex]), face_index)])

    result = bytearray(raw)
    changed, deltas = [], []
    by_material = collections.Counter()
    for vertex, values in candidates.items():
        if len(owners[vertex]) != 1 or not owners[vertex].issubset(allowed):
            continue
        if any(angle(values[0], value) > .01 for value in values[1:]):
            continue
        target = values[0]
        # Preserve sharp tips/unusual fans, then retain part of the old normal
        # so low-poly shading remains visible rather than globally rounding it.
        if angle(old[vertex], target) > 35.0:
            continue
        normal = unit(tuple((1 - BLEND) * a + BLEND * b for a, b in zip(unit(old[vertex]), target)))
        delta = angle(old[vertex], normal)
        if delta < .5:
            continue
        require(delta < 25.0, 'Normal rotation exceeds the safety limit')
        struct.pack_into('<3f', result, streams[9] + vertex * 12, *normal)
        changed.append(vertex)
        by_material[names[next(iter(owners[vertex]))]] += 1
        deltas.append(delta)

    require(changed, 'No meaningful normal changes found')
    new_normals = parse_static_backdrop(result)[5]
    start, end = streams[9], streams[9] + vertex_count * 12
    require(raw[:start] == result[:start] and raw[end:] == result[end:], 'Bytes outside normals changed')
    changed_set = set(changed)
    require(all(raw[start + i * 12:start + (i + 1) * 12] == result[start + i * 12:start + (i + 1) * 12]
                for i in range(vertex_count) if i not in changed_set), 'Unselected normal changed')
    require(all(all(math.isfinite(x) for x in normal) and .999 < length(normal) < 1.001
                for normal in new_normals), 'Output normals must be finite and unit length')
    require(len(raw) == len(result), 'File size changed')
    require(sha(result) == OUTPUT_SHA256[map_id], 'Output differs from the reviewed beta3 result')
    report = dict(map_id=map_id, relative=f'Data/Meshes/Objects/CXarena{map_id}.3da',
                  source_sha256=sha(raw), sha256=sha(result), bytes=len(raw),
                  vertices=vertex_count, triangles=face_count, normal_vertices_changed=len(changed),
                  changed_by_material=dict(by_material), crease_degrees=CREASE_DEGREES, blend=BLEND,
                  max_normal_change_degrees=max(deltas), mean_normal_change_degrees=sum(deltas) / len(deltas),
                  eligible_joined_edges=smooth_edges, preserved_sharp_edges=sharp_edges,
                  same_material_edge_fans=component_count, all_other_bytes_exact=True,
                  all_positions_uv_indices_materials_tracks_bounds_exact=True,
                  all_normals_unit_finite=True, textures_or_gameplay_resources_changed=False,
                  runtime_appearance_verified=False)
    return bytes(result), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True,
                        help='Read-only beta2 mod installation or reconstructed payload')
    parser.add_argument('--output', type=Path, required=True,
                        help='New separate output directory; never an installed game')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    require(source.is_dir(), 'Source directory missing')
    require(not output.exists(), 'Output must be new')
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            'Source and output must be disjoint')
    prepared = []
    # Validate/compute both maps before creating any output file.
    for map_id in (38, 40):
        relative = f'Data/Meshes/Objects/CXarena{map_id}.3da'
        file = (source / relative).resolve()
        require(file.is_relative_to(source) and file.is_file(), 'Required beta2 map missing: ' + relative)
        raw = file.read_bytes()
        data, report = polish_bytes(raw, map_id)
        prepared.append((file, data, report))
    require(all(sha(file.read_bytes()) == row['source_sha256'] for file, _, row in prepared),
            'Source changed while computing the candidate')
    output.mkdir(parents=True)
    for _, data, report in prepared:
        target = output / report['relative']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    receipt = dict(recipe=RECIPE_VERSION, files=[row for _, _, row in prepared],
                   source_game_modified=False, game_started=False,
                   unchanged_mesh_and_texture_memory=True, runtime_performance_claimed=False)
    (output / 'manifest.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
