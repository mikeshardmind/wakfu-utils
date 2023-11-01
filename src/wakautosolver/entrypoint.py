"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from enum import IntEnum

from restructured_types import DryRunResult, Result, SolveConfig


class Speed(IntEnum):
    near_instant = 1
    fast_spinner = 2
    slow_spinner = 3
    warn_user_before = 4


UserFacingWarning = str


def solve(cfg: SolveConfig) -> Result | DryRunResult:
    ...


def check_known_performance(cfg: SolveConfig) -> tuple[Speed, UserFacingWarning | None]:
    ...
