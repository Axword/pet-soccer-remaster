# Public installer delta format

The public package contains new mod assets and19 verified binary deltas. Complete
stock `code.pak`, `code_inf.pak`, `PetSoccer.bum`, engine DLLs, launcher and JRE
are absent. The installer reads the supported Polish game's files from the user's
installation, creates a separate checked copy, then applies the deltas there.

Each `patches.tsv` line contains five UTF-8 tab-separated values:

1. Original file SHA256 from `metadata/base-allowlist.tsv`.
2. Expected installed file SHA256.
3. Delta stream SHA256.
4. Relative installed file name.
5. Relative delta file name, below `.gmw-deltas/`.

Paths cannot be absolute, contain traversal/ADS components, collide, point through
junctions/symlinks, or name installer ownership metadata. Patched targets must be
present in the original allowlist. Standalone mod files cannot share a target.

## GMWDLT1 stream

All integers are unsigned little endian. Header:

- Eight bytes: `GMWDLT1` followed by NUL.
- `uint64`: base length, then target length.
- 32 raw bytes: SHA256 of the byte stream used as the delta base.
- 32 raw bytes: SHA256 of the reconstructed target.

Commands:

- `0x00`, `uint64 offset`, `uint64 length`: copy from the locally supplied base.
- `0x01`, `uint64 length`, literal bytes: append changed data.
- `0xff`: end, exactly at EOF and exactly at the declared target length.

Zero-length commands, out-of-bounds copies, oversized files, unknown commands,
truncation, trailing bytes, and every hash mismatch abort and roll back only the
installer's owned staging files. The native decoder streams through128KiB buffers;
it does not trust target lengths as memory allocation sizes.

## ZIP normalization for code.pak

Binary deflate streams can change when the same Java classes are repacked with
a different compressor. Delta-encoding those streams would unnecessarily embed
unchanged game code as literals. For `code.pak` only, both archives are first
normalized to a deterministic STORED ZIP:

- Entries sorted by their original names, with no entries added or removed.
- Every uncompressed entry byte preserved exactly.
- UTF-8 names, fixed DOS date1980-01-01, no extra fields or comments.
- Standard CRC32, local/central headers and EOCD, no ZIP64.

The small original `GMWZipNormalize.java` helper uses `java.util.zip` from the
user's already installed and hash-verified game JRE. It is run without an engine
or window, against the owned staging copy. Its compiled class is separately
hash-verified. A Python reference implementation in `delta.py` independently
produces byte-identical normalized archives.

The public installed archive has a different container hash from the private
compressed build, but **all entries and all Java class bytes are identical** to
that reviewed build. The new package's code delta stores128,482 bytes and copies
the unchanged class data from the user's original archive rather than bundling
the full game-code archive.

Runtime normalization tools and deltas stay in the installer's temporary payload;
they are not left in the installed game. The ownership ledger contains the final
reconstructed hashes. Uninstall preserves files the user has changed, including
their save, and files they have created.

## Rebuilding

`build_public_package.py` accepts `--base-game`, `--mod-profile`, `--base-manifest`
and `--output`. The mod profile is a reviewed private build directory containing
`payload.tsv` and `payload/`; the output must be new or empty. It never copies the
original game into the public payload. For ordinary installer rebuilding, use
the already published `package/` payload and compile the original helper/backend
and NSIS wrapper; no original game is needed just to compile the wrapper.

The ZIP helper class is pinned to SHA256
`100bc5030aba432464cd12ec97ab5f3b78b88da8bac23cd5b4299e60587120b0`.
If its source is intentionally changed/recompiled differently, update that hash
contract in `delta_format.h` and `build_public_package.py`, regenerate the payload,
then rerun the independent codec/native tests and complete installer smoke test.
