"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

from typing import Any

try:
    import msgpack  # type: ignore
except ModuleNotFoundError:
    _msg_avail = False
else:
    _msg_avail = True


try:
    import msgspec
except ModuleNotFoundError:
    _spec_avail = False
else:
    _spec_avail = True


def decode(raw: bytes) -> Any:  # noqa: ANN401
    if _spec_avail:
        return msgspec.msgpack.decode(raw)  # pyright: ignore[reportPossiblyUnboundVariable]
    if _msg_avail:
        return msgpack.unpackb(raw)  # type: ignore

    msg = "Must have either msgspec or msgpack available"
    raise RuntimeError(msg)


def encode(obj: Any) -> bytes:  # noqa: ANN401
    if _spec_avail:
        return msgspec.msgpack.encode(obj)  # pyright: ignore[reportPossiblyUnboundVariable]

    if _msg_avail:
        return msgpack.packb(obj)  # type: ignore

    msg = "Must have either msgspec or msgpack available"
    raise RuntimeError(msg)
