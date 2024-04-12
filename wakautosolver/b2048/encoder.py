"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# This is a pure python re-implementation of https://github.com/ionite34/base2048
# which is available under the MIT License here: https://github.com/ionite34/base2048/blob/main/LICENSE

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from io import StringIO
from typing import Generic, TypeVar

from .dec_table import dec as DEC_TABLE
from .enc_table import enc as ENC_TABLE

T = TypeVar("T")


class Peekable(Generic[T]):
    def __init__(self, iterable: Iterable[T]):
        self._it = iter(iterable)
        self._cache: deque[T] = deque()

    def __iter__(self):
        return self

    def has_more(self) -> bool:
        try:
            self.peek()
        except StopIteration:
            return False
        return True

    def peek(self) -> T:
        if not self._cache:
            self._cache.append(next(self._it))
        return self._cache[0]

    def __next__(self):
        if self._cache:
            return self._cache.popleft()
        return next(self._it)


TAIL = ("།", "༎", "༏", "༐", "༑", "༆", "༈", "༒")

ZERO_SET = {idx for idx, value in enumerate(DEC_TABLE) if value == 0xFFFF}


class DecodeError(Exception):
    pass


def encode(bys: bytes, /) -> str:
    ret = StringIO()
    stage = 0
    remaining = 0

    for byte in bys:
        need = 11 - remaining
        if need < 8:
            remaining = 8 - need
            index = (stage << need) | (byte >> remaining)
            ret.write(ENC_TABLE[index])
            stage = byte & ((1 << remaining) - 1)
        else:
            stage = (stage << 8) | byte
            remaining += 8

    if remaining > 0:
        ret.write(TAIL[stage] if remaining <= 3 else ENC_TABLE[stage])

    ret.seek(0)
    return ret.read()


def decode(string: str) -> bytes:
    ret: list[int] = []
    remaining = 0
    stage = 0
    chars = Peekable(enumerate(string))
    residue = 0

    for i, c in chars:
        residue = (residue + 11) % 8
        numeric = ord(c)

        if numeric > 4339:
            msg = f"Invalid character {i}: [{numeric}]"
            raise DecodeError(msg)

        n_new_bits, new_bits = 0, 0

        if numeric in ZERO_SET:
            if chars.has_more():
                i_next, c_next = chars.peek()
                msg = f"Unexpected character {i_next}: [{c_next}] after termination sequence {i}: [{c}]"
                raise DecodeError(msg)

            try:
                index = TAIL.index(c)
            except ValueError:
                msg = f"Invalid termination character {i}: [{c}]"
                raise DecodeError(msg) from None
            else:
                need = 8 - remaining
                if index < (1 << need):
                    n_new_bits = need
                    new_bits = index
                else:
                    msg = f"Invalid tail character {i}: [{c}]"
                    raise DecodeError(msg)
        else:
            new_bits = DEC_TABLE[numeric]
            n_new_bits = 11 if chars.has_more() else 11 - residue

        remaining += n_new_bits
        stage = (stage << n_new_bits) | new_bits
        while remaining > 8:
            remaining -= 8
            ret.append(stage >> remaining)
            stage &= (1 << remaining) - 1

    if remaining > 0:
        ret.append(stage >> (8 - remaining))

    return bytes(ret)
