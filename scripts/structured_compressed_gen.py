"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

import bz2
import json
import lzma
import struct
from io import BytesIO
from itertools import chain, starmap
from pathlib import Path
from typing import NamedTuple

import apsw


class Item(NamedTuple):
    # !IHBH37h
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


class LocaleData(NamedTuple):
    item_id: int
    en: str
    es: str
    fr: str
    pt: str


LocaleBundle = list[LocaleData]


class SourceData(NamedTuple):
    arch: frozenset[int]
    horde: frozenset[int]
    non_finite_arch_horde: frozenset[int]
    pvp: frozenset[int]
    ultimate_boss: frozenset[int]
    legacy_items: frozenset[int]
    blueprints: frozenset[int]


def pack_locale_data(locs: LocaleBundle) -> bytes:
    buffer = BytesIO()
    for item in locs:
        item_id, *strs = item
        bys = [s.encode() for s in strs]
        fmt = "!IB%dsB%dsB%dsB%ds" % tuple(map(len, bys))
        buffer.write(
            struct.pack(
                fmt, item_id, *chain.from_iterable(zip(map(len, bys), bys, strict=False))
            )
        )

    buffer.seek(0)
    return buffer.read()


def unpack_locale_data(packed: bytes) -> LocaleBundle:
    ret: LocaleBundle = []
    offset = 0
    while offset < len(packed):
        (item_id,) = struct.unpack_from("!I", packed, offset)
        offset += struct.calcsize("!I")

        strs: list[str] = []
        for _ in range(4):
            (s_len,) = struct.unpack_from("!B", packed, offset)
            offset += struct.calcsize("!B")
            fmt = "!%ds" % s_len
            (s,) = struct.unpack_from(fmt, packed, offset)
            offset += struct.calcsize(fmt)
            strs.append(s.decode("utf-8"))

        ret.append(LocaleData(item_id, *strs))

    return ret


def pack_sourcedata(data: SourceData) -> bytes:
    buffer = BytesIO()
    for item_set in data:
        ilen = len(item_set)
        fmt = "!I%dI" % ilen
        buffer.write(struct.pack(fmt, ilen, *item_set))
    buffer.seek(0)
    return buffer.read()


def unpack_sourcedata(packed: bytes) -> SourceData:
    offset = 0
    sets: list[frozenset[int]] = []
    while offset < len(packed):
        (ilen,) = struct.unpack_from("!I", packed, offset)
        offset += struct.calcsize("!I")
        fmt = "!%dI" % ilen
        items = frozenset(struct.unpack_from(fmt, packed, offset))
        sets.append(items)
        offset += struct.calcsize(fmt)

    return SourceData(*sets)


def pack_items(items: list[Item]) -> bytes:
    buffer = BytesIO()
    for item in items:
        buffer.write(struct.pack("!IHBH37h", *item))
    buffer.seek(0)
    return buffer.read()


def unpack_items(packed: bytes) -> list[Item]:
    return list(starmap(Item, struct.iter_unpack("!IHBH37h", packed)))


if __name__ == "__main__":
    base_path = Path(__file__).parent.with_name("wakautosolver") / "data"
    db_str = str(base_path / "items.db")
    conn = apsw.Connection(db_str)
    cursor = conn.cursor()
    rows = cursor.execute(
        """
        WITH ubs AS (SELECT item_id FROM unobtainable_items)
        SELECT * FROM items WHERE item_id not in ubs
        ORDER BY item_id ASC
        """
    )
    items = list(starmap(Item, rows))
    data = pack_items(items)
    compressed = lzma.compress(
        data, preset=lzma.PRESET_EXTREME, format=lzma.FORMAT_XZ, check=lzma.CHECK_NONE
    )
    with (base_path / "stat_only_bundle.xz").open(mode="wb") as fp:
        fp.write(compressed)

    rows = cursor.execute(
        """
        WITH ubs AS (SELECT item_id FROM unobtainable_items)
        SELECT item_id, en, es, fr, pt
        FROM items NATURAL JOIN item_names
        WHERE item_id not in ubs
        ORDER BY item_id ASC
        """
    )
    loc_items = list(starmap(LocaleData, rows))

    data = pack_locale_data(loc_items)
    bz2_comp = bz2.compress(data, compresslevel=9)
    with (base_path / "locale_bundle.bz2").open(mode="wb") as fp:
        fp.write(bz2_comp)

    data = [
        frozenset(
            i
            for (i,) in cursor.execute(f"SELECT item_id FROM [{table_name}]")  # noqa: S608
        )
        for table_name in (
            "archmonster_items",
            "horde_items",
            "ah_finite_exclusions",
            "pvp_items",
            "ub_items",
            "legacy_items",
            "blueprints",
        )
    ]

    datastruct = SourceData(*data)
    data = pack_sourcedata(datastruct)
    compressed = lzma.compress(
        data, preset=lzma.PRESET_EXTREME, format=lzma.FORMAT_XZ, check=lzma.CHECK_NONE
    )
    with (base_path / "source_info.xz").open(mode="wb") as fp:
        fp.write(compressed)

    export_path = base_path = Path(__file__).parent.with_name("exported_data")
    wakforge_exports = export_path / "wakforge"
    wakforge_exports.mkdir(parents=True, exist_ok=True)

    with (wakforge_exports / "item_sources.json").open(mode="w") as fp:
        data = {
            "arch": sorted(datastruct.arch),
            "horde": sorted(datastruct.horde),
            "non_finite_arch_horde": sorted(datastruct.non_finite_arch_horde),
            "pvp": sorted(datastruct.pvp),
            "ultimate_boss": sorted(datastruct.ultimate_boss),
            "legacy_items": sorted(datastruct.legacy_items),
            "blueprints": sorted(datastruct.blueprints),
        }
        json.dump(data, fp)
