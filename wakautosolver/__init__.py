"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

__version__ = "2023.10.29.post3"

from . import object_parsing, solver
from .b2048 import decode as b2048_decode
from .b2048 import encode as b2048_encode
from .build_compressor import decode_build, encode_build
from .unobs import get_unobtainable_ids
from .v1_entrypoint import SolveConfig, solve, solve_config  # pyright: ignore  # noqa: F401

# stuff in v1_entrypoint excluded from * import, only here for wakforge

__all__ = [
    "b2048_decode",
    "b2048_encode",
    "decode_build",
    "encode_build",
    "get_unobtainable_ids",
    "object_parsing",
    "solver",
]