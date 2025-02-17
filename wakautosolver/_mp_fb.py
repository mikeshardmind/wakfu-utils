"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

#: implements the subset of msgpack which we use

from __future__ import annotations

import struct
from io import BytesIO
from typing import TYPE_CHECKING, Any, cast


def _pack(buffer: BytesIO, obj: Any) -> None:
    buffer.seek(0, 2)

    if obj is None:
        buffer.write(b"\xc0")
    elif obj is True:
        buffer.write(b"\xc3")
    elif obj is False:
        buffer.write(b"\xc2")
    elif isinstance(obj, int):
        if 0 <= obj < 0x80:
            buffer.write(struct.pack("!B", obj))
        elif -0x20 <= obj < 0:
            buffer.write(struct.pack("!b", obj))
        elif 0x80 <= obj <= 0xFF:
            buffer.write(struct.pack("!BB", 0xCC, obj))
        elif -0x80 <= obj < 0:
            buffer.write(struct.pack("!Bb", 0xD0, obj))
        elif 0xFF < obj <= 0xFFFF:
            buffer.write(struct.pack("!BH", 0xCD, obj))
        elif -0x8000 <= obj < -0x80:
            buffer.write(struct.pack("!Bh", 0xD1, obj))
        elif 0xFFFF < obj <= 0xFFFFFFFF:
            buffer.write(struct.pack("!BI", 0xCE, obj))
        elif -0x80000000 <= obj < -0x8000:
            buffer.write(struct.pack("!Bi", 0xD2, obj))
        elif 0xFFFFFFFF < obj <= 0xFFFFFFFFFFFFFFFF:
            buffer.write(struct.pack("!BQ", 0xCF, obj))
        elif -0x8000000000000000 <= obj < -0x80000000:
            buffer.write(struct.pack("!Bq", 0xD3, obj))
        else:
            msg = "int outside of msgpack represntation support"
            raise ValueError(msg)

    elif isinstance(obj, (list, tuple)):
        if TYPE_CHECKING:
            obj = cast("list[object] | tuple[object, ...]", obj)

        n = len(obj)

        if n <= 0x0F:
            buffer.write(struct.pack("!B", 0x90 + n))
        elif n <= 0xFFFF:
            buffer.write(struct.pack("!BH", 0xDC, n))
        elif n <= 0xFFFFFFFF:
            buffer.write(struct.pack("!BI", 0xDD, n))
        else:
            raise ValueError

        for val in obj:
            _pack(buffer, val)
    else:
        msg = f"Unhandleable type {type(obj):!r}"
        raise TypeError(msg)


def pack(obj: object) -> bytes:
    buffer = BytesIO()
    _pack(buffer, obj)
    buffer.seek(0)
    return buffer.read()


def unpack(b: bytes) -> Any:
    buffer = BytesIO(b)
    buffer.seek(0)
    return _unpack(buffer)


def _unpack(buffer: BytesIO) -> Any:
    raw = buffer.read(1)
    s = raw[0]

    if s == 0xC0:
        return None
    if s == 0xC3:
        return True
    if s == 0xC2:
        return False
    if 0x00 <= s <= 0x7F:
        return s

    if 0xE0 <= s <= 0xFF:
        (ret,) = struct.unpack("!b", raw)
        return ret

    if 0x90 <= s <= 0x9F:
        return [_unpack(buffer) for _ in range(s - 0x90)]

    array_lookup = {0xDC: "!H", 0xDD: "!I"}

    if fmt := array_lookup.get(s):
        raw = buffer.read(struct.calcsize(fmt))
        (alen,) = struct.unpack(fmt, raw)
        return [_unpack(buffer) for _ in range(alen)]

    int_lookup = {
        0xCC: "!B",
        0xD0: "!b",
        0xCD: "!H",
        0xD1: "!h",
        0xCE: "!I",
        0xD2: "!i",
        0xCF: "!Q",
        0xD3: "!q",
    }

    if fmt := int_lookup.get(s):
        raw = buffer.read(struct.calcsize(fmt))
        (ret,) = struct.unpack(fmt, raw)
        return ret

    msg = "not our subset"
    raise ValueError(msg)
