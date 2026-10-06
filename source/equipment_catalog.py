"""Publisher-only category discovery from the certified ESM; never hand-maintained IDs."""

import mmap
import struct
import zlib

from kks_installer.engine import demand
from kks_installer.equipment import CATEGORIES


def equipment_categories(path):
    found = {name: set() for name in CATEGORIES}
    selected = {b"WEAP", b"ARMO", b"INNR"}
    with open(path, "rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
        def visit(start, end, depth=0):
            demand(depth <= 64, "ESM group nesting is too deep")
            pos = start
            while pos < end:
                demand(pos + 24 <= end, "Truncated ESM record header")
                sig, size, flags, fid = struct.unpack_from("<4sIII", data, pos)
                if sig == b"GRUP":
                    demand(size >= 24 and pos + size <= end, "Invalid ESM group bounds")
                    if fid != 0 or struct.pack("<I", flags) in selected:
                        visit(pos + 24, pos + size, depth + 1)
                    pos += size
                    continue
                demand(pos + 24 + size <= end, "Invalid ESM record bounds")
                if sig in selected:
                    demand(size <= 16 * 1024 * 1024, "Equipment ESM record is too large")
                    raw = data[pos + 24 : pos + 24 + size]
                    if flags & 0x40000:
                        demand(len(raw) >= 4, "Truncated compressed ESM record")
                        length = struct.unpack_from("<I", raw)[0]
                        demand(length <= 16 * 1024 * 1024, "Expanded ESM record is too large")
                        decoder = zlib.decompressobj()
                        raw = decoder.decompress(raw[4:], length + 1)
                        demand(decoder.eof and not decoder.unused_data and len(raw) == length,
                               "Invalid compressed ESM record")
                    offset, extended = 0, None
                    while offset < len(raw):
                        demand(offset + 6 <= len(raw), "Truncated ESM field")
                        field, length = struct.unpack_from("<4sH", raw, offset)
                        offset += 6
                        if field == b"XXXX":
                            demand(extended is None and length == 4 and offset + 4 <= len(raw),
                                   "Invalid extended ESM field")
                            extended = struct.unpack_from("<I", raw, offset)[0]
                            offset += 4
                            continue
                        if extended is not None:
                            length, extended = extended, None
                        demand(offset + length <= len(raw), "Invalid ESM field bounds")
                        category = sig.decode("ascii") + ":" + field.decode("ascii")
                        if category in found:
                            demand(length == 4, "Expected a localized equipment string reference")
                            sid = struct.unpack_from("<I", raw, offset)[0]
                            if sid:
                                found[category].add(sid)
                        offset += length
                    demand(extended is None, "Dangling extended ESM field")
                pos += 24 + size
        visit(0, len(data))
    demand(all(found.values()), "ESM does not contain the complete equipment naming categories")
    return {name: sorted(found[name]) for name in CATEGORIES}
