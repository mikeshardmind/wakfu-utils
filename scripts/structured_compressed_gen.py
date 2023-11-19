"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

import bz2

import apsw
from msgspec import Struct, msgpack


class Item(Struct, array_like=True):
    item_id: int
    item_lv: int
    item_rarity: int
    item_type: int
    hp: int = 0
    ap: int = 0
    mp: int = 0
    wp: int = 0
    ra: int = 0
    control: int = 0
    block: int = 0
    critical_hit: int = 0
    dodge: int = 0
    lock: int = 0
    force_of_will: int = 0
    rear_mastery: int = 0
    healing_mastery: int = 0
    melee_mastery: int = 0
    distance_mastery: int = 0
    berserk_mastery: int = 0
    critical_mastery: int = 0
    fire_mastery: int = 0
    earth_mastery: int = 0
    water_mastery: int = 0
    air_mastery: int = 0
    mastery_1_element: int = 0
    mastery_2_elements: int = 0
    mastery_3_elements: int = 0
    elemental_mastery: int = 0
    resistance_1_element: int = 0
    resistance_2_elements: int = 0
    resistance_3_elements: int = 0
    fire_resistance: int = 0
    earth_resistance: int = 0
    water_resistance: int = 0
    air_resistance: int = 0
    elemental_resistance: int = 0
    rear_resistance: int = 0
    critical_resistance: int = 0
    armor_given: int = 0
    armor_received: int = 0


StatOnlyBundle = list[Item]

if __name__ == "__main__":
    conn = apsw.Connection("items.db")
    rows = conn.cursor().execute("SELECT * FROM items order by item_id ASC;").fetchall()
    items = [Item(*row) for row in rows]  # type: ignore
    data = msgpack.encode(items)
    # ensure roundtrip
    items_2 = msgpack.decode(data, type=StatOnlyBundle)
    assert items == items_2

    bz2_comp = bz2.compress(data, compresslevel=9)
    with open("stat_only_bundle.bz2", mode="wb") as fp:
        fp.write(bz2_comp)