"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec

P = ParamSpec("P")


def only_once(f: Callable[P, object]) -> Callable[P, None]:
    has_called = False

    def wrapped(*args: P.args, **kwargs: P.kwargs) -> None:
        nonlocal has_called

        if not has_called:
            has_called = True
            f(*args, **kwargs)

    return wrapped
