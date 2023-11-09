"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

import pathlib
import sys

import msgspec

from .solver import entrypoint, v1Config

if __name__ == "__main__":
    ns = None
    if n := sys.argv[1]:
        path = pathlib.Path(n).resolve()
        if path.exists():
            with path.open(mode="rb") as fp:
                ns = msgspec.toml.decode(fp.read(), type=v1Config)

    entrypoint(sys.stdout, ns)
