"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import bz2
from pathlib import Path

import msgspec

"""
Exists just to generate a smaller file intended for use in minimal distributions
"""

if __name__ == "__main__":
    base_path = Path(__file__).parent
    with (base_path / "json_data" / "items.json").open(mode="rb") as fp:
        data = msgspec.json.decode(fp.read())

    # Fully math based tools don't need the flavor text
    data = [{k: v for k, v in i.items() if k != "description"} for i in data]

    packed = msgspec.msgpack.encode(data)  # smaller more efficient than json to start
    compressed_bz2 = bz2.compress(packed)
    # for this data set, bz2 using highest compression level (which is default)
    # outperforms lzma and gzip,
    # both with defaults and with attempts at adaptive tuning.
    with (base_path / "item_data.bz2").open(mode="wb") as fp:
        fp.write(compressed_bz2)
