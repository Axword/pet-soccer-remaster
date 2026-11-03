# Asset algorithms added in Online beta 1

These Python sources are the authored geometry and texture algorithms. They do
not include the base game, extracted meshes, texture atlases, generated artwork,
or converted characters from other games. Inputs must be supplied locally.

Install Python 3.10 or later and the dependencies in `requirements.txt`.
The export was checked with Python 3.13.13, NumPy 2.3.4 and Pillow 13.0.0. These tools
do not start Pet Soccer or Blender. Use a working directory outside the game.
Every generator requires explicit input/output paths; it refuses output inside
its source game. Outputs below are examples of isolated work directories.

## Original maps and animal identities

```powershell
python authoring/features/base-maps/build_stock_polish.py --game 'C:\Gry\Pet Soccer' --output build/stock-polish
python authoring/features/animal-identity/build_variants.py --all --game 'C:\Gry\Pet Soccer' --output build/animal-identity
python authoring/features/animal-identity/build_texture_variants.py --all --game 'C:\Gry\Pet Soccer' --output build/animal-identity
```

The map pass keeps existing dimensions and mip counts, terrain geometry,
lighting, markings and collision inputs. It modifies only the existing terrain
albedo PNG/TEX pairs, with bounded luminance/mean-colour differences. Smaller
native mips remain byte-identical.

The identity pass creates seven variants for each of the twelve original clubs.
It uses the original bone influences and animation tracks, rather than a new
rig. The texture pass changes only eligible fur/skin/metal blocks, preserving
shirt and eye regions and the original prepared-cache layout. Native Java code
separately preserves stock gameplay bounds; the exported mesh variants alone do
not prove gameplay equivalence.

## Jagniellonia

Supply local artwork as `lamb.png`, `kit-02.png` to `kit-05.png`, `crest.png` and
`barn.png`. These are inputs, not downloaded automatically or embedded in these
source files. The original bear mesh/INI and eye atlas are read from the game.

```powershell
python authoring/features/jagniellonia/build_lamb_one.py --game 'C:\Gry\Pet Soccer' --texture build/artwork/lamb.png --output build/jagniellonia
python authoring/features/jagniellonia/build_assets.py --game 'C:\Gry\Pet Soccer' --artwork-dir build/artwork --output build/jagniellonia
python authoring/features/jagniellonia/build_map.py --game 'C:\Gry\Pet Soccer' --polish-overlay build/stock-polish/overlay --barn-texture build/artwork/barn.png --output build/jagniellonia
```

`build_assets.py` requires the approved first-lamb geometry hash before creating
the other six identities. The eye repair is deliberately the **last geometry
operation**, after every head/body morph, for each of the seven output models.
It makes the white eye caps smaller and fits them to the head, then appends two
eye-only skinned nodes for the conforming round pupils. It preserves original
non-eye geometry, tracks, weights and textures. Original LOD2 has no eyes and
remains untouched. Already repaired models containing `Oczy_` nodes are rejected
to prevent another shrink or duplicate pupils.

The first-lamb recipe pins its exact supported original bear mesh and eleven
authored output normal components. The seven fixed morph profiles additionally
use the small `canonical-normal-components.json` table of accepted authored
normal components. This preserves the accepted degenerate low-LOD result and
avoids numeric-library rounding making the hash-checked next stage fail.
The table contains no positions, UVs, original mesh data, animation or skin
weights. Each canonicalized raw model must match its reviewed SHA256 before the
eye repair is applied. An unsupported numeric build or a modified profile fails
explicitly instead of silently publishing different models.

For an existing **raw, pre-repair** seven-model overlay, the same final step can
be run separately. Do not run this again on output from the current
`build_assets.py`:

```powershell
python authoring/features/eyes-fix/build_eye_delta.py --input build/raw-jagniellonia/overlay --output build/repaired-eyes
```

`expected-inputs.json` pins the seven reviewed pre-repair meshes. The standalone
tool validates all requested source hashes and the approved candidate0 output;
the algorithm also rejects already repaired input. `inspect_eyes.py` can read a
locally prepared overlay without a renderer. `native_readback.py` is a CPU mesh
renderer library, not evidence of a successful native-engine test.

The new stadium reuses the original farm's pitch and restart envelope, with
equal-length native map reference edits and a barn material change. Its map ID
and team registration are handled by the separate Java/native source patches.

The source mapping and checksums are in `../online-authoring-provenance.json`.
Algorithm checks are separate from visual acceptance in a real match: compiling
these scripts or reproducing model bytes does not establish that the camera,
animation, field transitions or UI work in the engine.
