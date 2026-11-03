"""Small luminance-only polish of current stock terrain albedos.

This offline asset pipeline never starts an engine or changes any installed game.
Native BC1 cache layout is pinned/parsed from the current actual source files.
"""
from pathlib import Path
import argparse, hashlib, io, json, re, struct, sys

ROOT = Path(__file__).resolve().parent
SOURCE = None
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from native_tex import encode_bc1, assemble_tex

MAPS = ['Kurczaki', 'Zaby', 'Zolwie', 'Pantery', 'Rekiny', 'Goryle',
        'Niedzwiedzie', 'Lwy', 'Zyrafy', 'Byki', 'Dinozaury', 'Robociki']
sha = lambda data: hashlib.sha256(data).hexdigest()


def read_tex(data):
    assert data[:4] == bytes.fromhex('01afdabc'), 'Unknown native texture magic'
    encoding, width, height = struct.unpack_from('<3I', data, 4)
    assert (encoding, width, height) == (1, 1024, 1024), 'Unknown stock BC1 layout'
    pos, chunks = 16, []
    for level in range(11):
        index, size = struct.unpack_from('<2I', data, pos)
        w, h = max(1, width >> level), max(1, height >> level)
        assert index == level and size == max(1, (w + 3)//4) * max(1, (h + 3)//4) * 8
        pos += 8
        assert pos + size <= len(data)
        chunks.append(data[pos:pos+size]); pos += size
    assert pos == len(data), 'Unexpected native mip tail'
    return chunks


def decode_bc1(data, size):
    return Image.frombytes('RGBA', size, data, 'bcn', (1, 'DXT1')).convert('RGB')


def refine_bc1(original, size):
    """Keep every original RGB565 endpoint; only refine nearby palette indices.

    Recompressing a legacy BC1 cache can bias its colour. Reusing its exact
    palettes avoids this and keeps large art/shadow/marking transitions intact.
    """
    before = decode_bc1(original, size)
    target, _ = polish(before)
    data = np.frombuffer(original, dtype=np.uint8).reshape(-1, 8).copy()
    c0 = data[:, 0].astype(np.uint32) | data[:, 1].astype(np.uint32) << 8
    c1 = data[:, 2].astype(np.uint32) | data[:, 3].astype(np.uint32) << 8
    def rgb565(c):
        r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
        return np.stack(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)), axis=1).astype(np.int16)
    p0, p1 = rgb565(c0), rgb565(c1)
    palette = np.stack((p0, p1, (2*p0+p1)//3, (p0+2*p1)//3), axis=1)
    three = c0 <= c1
    palette[three, 2] = ((p0+p1)//2)[three]; palette[three, 3] = 0
    bits = sum(data[:, 4+i].astype(np.uint32) << (8*i) for i in range(4))
    shift = np.arange(16, dtype=np.uint32)*2
    previous = ((bits[:, None] >> shift) & 3).astype(np.int64)
    w, h = size
    pixels = np.asarray(target, dtype=np.int16).reshape(h//4, 4, w//4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3)
    before_pixels = np.asarray(before, dtype=np.int16).reshape(h//4, 4, w//4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3)
    distance = ((pixels[:, :, None, :].astype(np.int32)-palette[:, None, :, :])**2).sum(3)
    distance[three, :, 3] = 1000000  # Never create a transparent/black index.
    selected = distance.argmin(2)
    old_error = np.take_along_axis(distance, previous[:, :, None], axis=2)[:, :, 0]
    new_error = np.take_along_axis(distance, selected[:, :, None], axis=2)[:, :, 0]
    old_colour = palette[np.arange(len(data))[:, None], previous]
    new_colour = palette[np.arange(len(data))[:, None], selected]
    changed = ((pixels != before_pixels).any(2) & (new_error+2 < old_error)
               & (np.abs(new_colour-old_colour).max(2) <= 8))
    changed[three] &= previous[three] != 3
    selected = np.where(changed, selected, previous).astype(np.uint32)
    updated = (selected << shift).sum(1).astype(np.uint32)
    for i in range(4): data[:, 4+i] = ((updated >> (8*i)) & 255).astype(np.uint8)
    result = data.tobytes()
    assert np.array_equal(data[:, :4], np.frombuffer(original, dtype=np.uint8).reshape(-1, 8)[:, :4])
    return result, int(changed.sum())


def polish(image):
    rgb = np.asarray(image.convert('RGB'), dtype=np.int16)
    # Small local luminance contrast, no generated grain, hue shift, painting,
    # scale change, global exposure adjustment or changes to existing shadows.
    luminance = image.convert('L')
    blurred = np.asarray(luminance.filter(ImageFilter.GaussianBlur(.85)), dtype=np.int16)
    detail = np.asarray(luminance, dtype=np.int16) - blurred
    broad = np.asarray(luminance.filter(ImageFilter.GaussianBlur(3)), dtype=np.int16)
    local = np.asarray(luminance, dtype=np.int16)-broad
    delta = np.rint(np.clip(detail*.40+local*.08,-5,5)).astype(np.int16)
    delta[np.abs(detail) < 3] = 0
    delta = np.maximum(-rgb.min(2), np.minimum(255-rgb.max(2), delta))
    # Keep bright neutral markings/highlights byte-identical in the PNG.
    protected = (rgb.min(2) >= 220) & ((rgb.max(2)-rgb.min(2)) <= 35)
    delta[protected] = 0
    result = (rgb + delta[:, :, None]).astype(np.uint8)
    assert np.array_equal(result[protected], rgb[protected])
    # Equal per-channel displacement preserves original hue and channel order.
    difference = result.astype(np.int16)-rgb
    assert np.array_equal(difference[:, :, 0], difference[:, :, 1])
    assert np.array_equal(difference[:, :, 0], difference[:, :, 2])
    assert abs(difference).max() <= 5
    return Image.fromarray(result, 'RGB'), int(protected.sum())


def main():
    global SOURCE
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', required=True, type=Path, help='Read-only source game directory')
    parser.add_argument('--output', required=True, type=Path, help='Fresh isolated delivery directory')
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    SOURCE = args.game.resolve(strict=True)
    output = args.output.resolve()
    assert not output.is_relative_to(SOURCE), 'Output must be outside the source game'
    assert not output.exists(), 'Never overwrite a delivery; choose a fresh name'
    output.mkdir(parents=True); evidence = output / 'evidence'; evidence.mkdir()
    payload = output / 'overlay'
    source_inventory, changes, maps = [], [], []
    selected_maps=['Kurczaki','Niedzwiedzie','Rekiny'] if args.preview_only else MAPS
    board = Image.new('RGB', (1536, ((len(selected_maps)+2)//3)*282), (24, 28, 25)); draw = ImageDraw.Draw(board)
    # Pin all immediate map/gameplay/height/shadow/colour files. Existing LMaps
    # directories are outside the allowlisted overlay and are never copied.
    for name in selected_maps:
        folder = SOURCE / 'Data' / 'Levels' / name
        for path in sorted(folder.iterdir()):
            if path.is_file():
                source_inventory.append({'path':path.relative_to(SOURCE).as_posix(),
                                         'sha256':sha(path.read_bytes()), 'bytes':path.stat().st_size})
    pinned = {row['path']:row['sha256'] for row in source_inventory}
    for number, name in enumerate(selected_maps):
        folder = SOURCE / 'Data' / 'Levels' / name
        png = folder / ('PS_C_'+name+'.png'); tex = folder / ('ps_c_'+name.lower()+'.tex')
        old_png, old_tex = png.read_bytes(), tex.read_bytes()
        original = Image.open(io.BytesIO(old_png)).convert('RGB')
        assert original.size == (1024, 1024)
        after, protected = polish(original)
        chunks = read_tex(old_tex)
        native_before = decode_bc1(chunks[0], original.size)
        new_chunks = []; changed_indices = []
        for level, chunk in enumerate(chunks):
            # Keep small/distant native mip levels byte-identical. The slight
            # polish affects only1024/512/256/128, with no extra memory or LODs.
            if level < 4:
                mip=after if level==0 else after.resize((1024>>level,1024>>level),Image.Resampling.LANCZOS)
                reference=np.asarray(decode_bc1(chunk,mip.size),dtype=np.float32).mean((0,1))
                updated=encode_bc1(mip,mean_rgb=reference)
                changed_indices.append(sum(a!=b for a,b in zip(chunk,updated)))
                chunk=updated
            new_chunks.append(chunk)
        new_tex = old_tex[:16] + b''.join(struct.pack('<2I', i, len(c))+c for i, c in enumerate(new_chunks))
        assert len(new_tex) == len(old_tex)
        assert read_tex(new_tex)[4:] == chunks[4:]
        native_after = decode_bc1(new_chunks[0], original.size)
        native_before.save(evidence / (name+'-native-before.png'))
        native_after.save(evidence / (name+'-native-after.png'))
        # Same pixel crop/scale within every pair; these are texture readbacks,
        # not a simulated in-game screenshot or proof of terrain rendering.
        crop = (360, 265, 665, 765)
        a = native_before.crop(crop).resize((248, 407), Image.Resampling.LANCZOS)
        b = native_after.crop(crop).resize((248, 407), Image.Resampling.LANCZOS)
        pair = Image.new('RGB', (512, 445), (24, 28, 25)); pd = ImageDraw.Draw(pair)
        pd.text((8, 5), name+' | PRZED / PO', fill=(240, 240, 230))
        pair.paste(a, (5, 30)); pair.paste(b, (259, 30))
        pair.save(evidence/(name+'-pitch-pair.png'))
        # The contact sheet keeps full terrain identity visible.
        x, y = (number % 3)*512, (number // 3)*282
        draw.text((x+5, y+4), name+' | PRZED / PO', fill=(240, 240, 230))
        board.paste(native_before.resize((256, 256), Image.Resampling.LANCZOS), (x, y+22))
        board.paste(native_after.resize((256, 256), Image.Resampling.LANCZOS), (x+256, y+22))
        native_a, native_b = np.asarray(native_before, dtype=np.int16), np.asarray(native_after, dtype=np.int16)
        error = np.abs(native_b-native_a)
        assert 0 < error.mean() < 6, 'Native polish must remain modest'
        assert np.abs(native_b.mean((0, 1))-native_a.mean((0, 1))).max() < 1
        for source_path in (png, tex):
            relative = source_path.relative_to(SOURCE)
            destination = payload / relative; destination.parent.mkdir(parents=True, exist_ok=True)
            if source_path == png: after.save(destination, optimize=True)
            else: destination.write_bytes(new_tex)
            changes.append({'path':relative.as_posix(),'source_sha256':pinned[relative.as_posix()],
                            'sha256':sha(destination.read_bytes()),'source_bytes':source_path.stat().st_size,
                            'bytes':destination.stat().st_size})
        scene = (folder / (name+'.map')).read_bytes()
        refs = [m[0].decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{4,}', scene)
                if any(k in m[0].lower() for k in (b'ps_h_', b'ps_s_', b'ps_c_', b'field', b'ground'))]
        maps.append({'name':name,'size':[1024,1024],'mip_count':11,'native_bytes':len(new_tex),
                     'unchanged_native_mip_levels':list(range(4,11)),'protected_png_pixels':protected,
                     'native_mean_absolute_channel_change':float(error.mean()),
                     'native_colour_mean_controlled':True,'changed_bc1_bytes_per_mip':changed_indices,
                     'native_mean_rgb_before':native_a.mean((0,1)).tolist(),
                     'native_mean_rgb_after':native_b.mean((0,1)).tolist(),'map_references':refs})
        print('Stock texture:',name,flush=True)
    board.save(evidence/'stock12-before-after.png')
    assert all(sha((SOURCE/row['path']).read_bytes()) == row['sha256'] for row in source_inventory)
    manifest = {'source_root':str(SOURCE),'algorithm':'same-size PNG luminance-only local contrast delta<=5; native BC1 re-encoding with bounded original mean-RGB correction',
                'source_inventory':source_inventory,'files':changes,'maps':maps,
                'textures_changed':len(changes),'preview_only':args.preview_only,'native_texture_memory_delta_bytes':0,
                'map_geometry_height_shadow_density_collision_files_changed':False,
                'all_input_files_unchanged':True,'native_game_launched':False,'native_runtime_verified':False,
                'evidence_scope':'Offline native BC1 texture decode readback, same framing before/after; not engine screenshots',
                'script_sha256':sha(Path(__file__).read_bytes())}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'output':str(output),'maps':len(selected_maps),'files':len(changes),'native_memory_delta':0,
                      'max_native_mean_absolute_delta':max(row['native_mean_absolute_channel_change']for row in maps)}), flush=True)


if __name__ == '__main__':
    main()
