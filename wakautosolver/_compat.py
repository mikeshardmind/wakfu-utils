"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

from typing import Any

from ._mp_fb import pack, unpack


def decode(raw: bytes) -> Any:
    return unpack(raw)


def encode(obj: Any) -> bytes:
    return pack(obj)
