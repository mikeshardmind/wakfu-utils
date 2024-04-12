"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import zlib

from msgspec import Struct, field, msgpack

from . import __version__ as ver
from . import b2048
from .restructured_types import StatPriority
from .wakforge_buildcodes import Buildv1 as WFB


class v2BuildConfig(Struct, array_like=True):  # temporary
    build_code: WFB = field(default_factory=WFB)
    stat_priorities: StatPriority = field(default_factory=StatPriority)


class Wakforge_v2ShortError(Struct, array_like=True):
    version: str = field(default=ver)
    solve_params: v2BuildConfig = field(default_factory=v2BuildConfig)
    message: str = ""

    def pack(self) -> str:
        compressor = zlib.compressobj(level=9, wbits=-15)
        packed = msgpack.encode(self)

        return b2048.encode(compressor.compress(packed) + compressor.flush())

    @classmethod
    def from_packed(cls: type[Wakforge_v2ShortError], s: str, /) -> Wakforge_v2ShortError:
        return msgpack.decode(zlib.decompress(b2048.decode(s), wbits=-15), type=cls)
