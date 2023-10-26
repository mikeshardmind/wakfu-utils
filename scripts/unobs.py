"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from collections.abc import Iterator

"""
Manually tracked items that aren't currently obtainable, grouped by reason if known
"""



# https://www.wakfu.com/en/forum/8-general-discussions/239875-nemotilus-weapons
"""
│ 20790   │ Nemotilus Harpoon    │
│ 20791   │ Nemotilus Bolt-Screw |
"""

## old krosmaster rewards
"""
| 15284   │ Kroraging Helmet      │
│ 15285   │ Krotector Helmet      │
│ 15286   │ Krolevel Helmet       │
│ 15287   │ Krospeed Helmet       │
│ 15288   │ Kroraging Torso       │
│ 15289   │ Krotector Torso       │
│ 15290   │ Krolevel Torso        │
│ 15291   │ Krospeed Torso        │
│ 15292   │ Kroraging Cloak       │
│ 15293   │ Krotector Cloak       │
│ 15294   │ Krolevel Cloak        │
│ 15295   │ Krospeed Cloak        │
│ 15296   │ Kroraging Epaulettes  │
│ 15297   │ Krotector Epaulettes  │
│ 15298   │ Krolevel Epaulettes   │
│ 15299   │ Krospeed Epaulettes   |
"""

# old crafts
"""
│ 12836 | Fuzzy Cards  |
"""

_krosmaster: list[int] = [
    15284,
    15285,
    15286,
    15287,
    15288,
    15289,
    15290,
    15291,
    15292,
    15293,
    15294,
    15295,
    15296,
    15297,
    15298,
    15299,
]

_nemotilus: list[int] = [
    20790,
    20791,
]

_old_crafts: list[int] = [
    12836,
]

_unknown: list[int] = []


_item_map: dict[str, list[int]] = {
    "Krosmaster rewards": _krosmaster,
    "Old crafts": _old_crafts,
    "Unknown": _unknown,
    "Items that were only ever on beta (so far?)": _nemotilus,
}


def get_unobtainable_info() -> Iterator[tuple[int, str]]:
    for reason, item_ids in _item_map.items():
        for item_id in item_ids:
            yield (item_id, reason)

def get_unobtainable_ids() -> Iterator[int]:
    for item_ids in _item_map.values():
        yield from item_ids