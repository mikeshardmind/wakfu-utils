"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# Note: This is Year, month, monotonic not year, month, day
__version__ = "2024.07.1"

from . import object_parsing, solver
from .b2048 import decode as b2048_decode
from .b2048 import encode as b2048_encode

__all__ = [
    "b2048_decode",
    "b2048_encode",
    "object_parsing",
    "solver",
]
