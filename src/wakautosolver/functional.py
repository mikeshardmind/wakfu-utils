"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")


class Reduction(Protocol[T]):
    def __call__(self, args: Iterable[T], /) -> T:
        ...


def element_wise_apply(func: Reduction[T], seq: Iterable[Iterable[T]]) -> Iterable[T]:
    return (*(func(*args) for args in zip(*seq, strict=True)),)


def multiple_apply_element_wise(funcs: Iterable[Reduction[T]], data: Iterable[Iterable[T]]) -> Iterable[Iterable[T]]:
    return [element_wise_apply(func, data) for func in funcs]
