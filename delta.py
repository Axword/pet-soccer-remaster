"""GMWDLT1 copy/literal delta encoder and independent reference decoder.

The stream stores hashes and only target bytes absent from matching base runs.
Integers are unsigned little endian. No third-party package is required.
"""
import hashlib
import struct
import io
import zipfile
import zlib

MAGIC = b'GMWDLT1\0'
U64 = struct.Struct('<Q')
MAXIMUM = 1024 ** 3


def normalize_zip(data):
    body, central = bytearray(), bytearray()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entry')
        for name in sorted(names):
            encoded = name.encode('utf8')
            value = archive.read(name)
            crc, offset = zlib.crc32(value), len(body)
            body += struct.pack('<IHHHHHIIIHH', 0x04034b50, 20, 0, 0, 0, 33, crc, len(value), len(value), len(encoded), 0)
            body += encoded + value
            central += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 20, 20, 0, 0, 0, 33, crc, len(value), len(value), len(encoded), 0, 0, 0, 0, 0, offset)
            central += encoded
    return bytes(body + central + struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(names), len(names), len(central), len(body), 0))


def encode(base, target):
    if len(base) > MAXIMUM or len(target) > MAXIMUM:
        raise ValueError('Delta file size exceeds 1 GiB')
    output = bytearray(MAGIC + U64.pack(len(base)) + U64.pack(len(target)))
    output += hashlib.sha256(base).digest() + hashlib.sha256(target).digest()
    # Fixed source block indexing avoids SequenceMatcher's quadratic behavior on
    # compressed binary data. Scan target bytewise so insertions keep matching.
    index = {}
    for offset in range(0, max(0, len(base) - 15), 16):
        key = base[offset:offset + 16]
        positions = index.setdefault(key, [])
        if len(positions) < 4:
            positions.append(offset)
    cursor = literal_start = copied = literals = commands = 0
    while cursor + 16 <= len(target):
        best_offset = best_length = 0
        for offset in index.get(target[cursor:cursor + 16], ()):
            length, limit = 16, min(len(base) - offset, len(target) - cursor)
            while length < limit:
                count = min(4096, limit - length)
                if base[offset + length:offset + length + count] == target[cursor + length:cursor + length + count]:
                    length += count
                    continue
                lo, hi = 0, count
                while lo < hi:
                    middle = (lo + hi + 1) // 2
                    if base[offset + length:offset + length + middle] == target[cursor + length:cursor + length + middle]:
                        lo = middle
                    else:
                        hi = middle - 1
                length += lo
                break
            if length > best_length:
                best_offset, best_length = offset, length
        if best_length < 32:
            cursor += 1
            continue
        if cursor > literal_start:
            data = target[literal_start:cursor]
            output += b'\x01' + U64.pack(len(data)) + data
            literals += len(data)
            commands += 1
        output += b'\x00' + U64.pack(best_offset) + U64.pack(best_length)
        copied += best_length
        commands += 1
        cursor += best_length
        literal_start = cursor
    if literal_start < len(target):
        data = target[literal_start:]
        output += b'\x01' + U64.pack(len(data)) + data
        literals += len(data)
        commands += 1
    output += b'\xff'
    return bytes(output), {'copy_bytes': copied, 'literal_bytes': literals,
                           'commands': commands, 'delta_bytes': len(output)}


def apply(base, delta):
    if len(delta) < 89 or delta[:8] != MAGIC:
        raise ValueError('Unsupported or truncated delta')
    base_size, target_size = struct.unpack_from('<QQ', delta, 8)
    if base_size != len(base) or max(base_size, target_size, len(delta)) > MAXIMUM:
        raise ValueError('Invalid delta sizes')
    if hashlib.sha256(base).digest() != delta[24:56]:
        raise ValueError('Wrong original file')
    expected = delta[56:88]
    cursor = 88
    output = bytearray()
    while cursor < len(delta):
        command = delta[cursor]
        cursor += 1
        if command == 255:
            if cursor != len(delta) or len(output) != target_size or hashlib.sha256(output).digest() != expected:
                raise ValueError('Delta result does not match header')
            return bytes(output)
        if command not in (0, 1):
            raise ValueError('Unknown command')
        count = 16 if command == 0 else 8
        if cursor + count > len(delta):
            raise ValueError('Truncated command')
        if command == 0:
            offset, length = struct.unpack_from('<QQ', delta, cursor)
            cursor += 16
            if offset > base_size or length > base_size - offset:
                raise ValueError('Original copy out of range')
            data = base[offset:offset + length]
        else:
            length = U64.unpack_from(delta, cursor)[0]
            cursor += 8
            if cursor + length > len(delta):
                raise ValueError('Truncated literal')
            data = delta[cursor:cursor + length]
            cursor += length
        if not length or length > target_size - len(output):
            raise ValueError('Target copy out of range')
        output += data
    raise ValueError('Missing end command')
