"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

from typing import Literal

# Imagine having real refinement types...
# Nah, just let everyone suffer or make libraries do things
# like this or use annotated for type info.
# And *yes* I know msgspec.Meta exists,
# but that means other things need to understand msgspec.Meta
# to benefit from the more precise type info
# annotated should not have been used as a standin for refinement types

# fmt: off
ZERO_OR_ONE = Literal[0, 1]
UP_TO_5     = Literal[0, 1, 2, 3, 4, 5]
UP_TO_10    = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
UP_TO_11    = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
UP_TO_20    = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

UP_TO_40    = Literal[
                                                                                             0,
                 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]

STAT_MAX    = Literal[
                                                                                             0,
                 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
                41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58]

# fmt: on
