"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import bz2

import msgspec

"""
Exists just to generate a smaller file intended for use in minimal distributions
"""

if __name__ == "__main__":
    with open("json_data/items.json", mode="rb") as fp:
        data = msgspec.json.decode(fp.read())

    # Fully math based tools don't need the flavor text
    data = [{k: v for k, v in i.items() if k != "description"} for i in data]

    packed = msgspec.msgpack.encode(data)  # smaller more efficient than json to start
    compressed_bz2 = bz2.compress(packed)
    # for this data set, bz2 using highest compression level (which is default)
    # outperforms lzma and gzip,
    # both with defaults and with attempts at adaptive tuning.
    with open("item_data.bz2", mode="wb") as fp:
        fp.write(compressed_bz2)
