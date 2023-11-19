"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# pyright: reportPrivateUsage=none

import json
import re

import apsw

from wakautosolver import object_parsing, unobs

ITEM_TYPE_MAP = object_parsing.ITEM_TYPE_MAP

SCHEMA = """
CREATE TABLE IF NOT EXISTS blueprints (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS ub_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS pvp_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS archmonster_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS horde_items (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS recipes (
    item_id INTEGER PRIMARY KEY NOT NULL,
    is_upgrade INTEGER NOT NULL DEFAULT FALSE,
    upgrade_of INTEGER NOT NULL DEFAULT 0
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY NOT NULL,
    item_lv INTEGER NOT NULL,
    item_rarity INTEGER NOT NULL,
    item_type INTEGER NOT NULL,
    hp INTEGER NOT NULL DEFAULT 0,
    ap INTEGER DEFAULT 0,
    mp INTEGER DEFAULT 0,
    wp INTEGER DEFAULT 0,
    range INTEGER DEFAULT 0,
    control INTEGER DEFAULT 0,
    block INTEGER DEFAULT 0,
    critical_hit INTEGER DEFAULT 0,
    dodge INTEGER DEFAULT 0,
    lock INTEGER DEFAULT 0,
    force_of_will INTEGER DEFAULT 0,
    rear_mastery INTEGER DEFAULT 0,
    healing_mastery INTEGER DEFAULT 0,
    melee_mastery INTEGER DEFAULT 0,
    distance_mastery INTEGER DEFAULT 0,
    berserk_mastery INTEGER DEFAULT 0,
    critical_mastery INTEGER DEFAULT 0,
    fire_mastery INTEGER DEFAULT 0,
    earth_mastery INTEGER DEFAULT 0,
    water_mastery INTEGER DEFAULT 0,
    air_mastery INTEGER DEFAULT 0,
    mastery_1_element INTEGER DEFAULT 0,
    mastery_2_elements INTEGER DEFAULT 0,
    mastery_3_elements INTEGER DEFAULT 0,
    elemental_mastery INTEGER DEFAULT 0,
    resistance_1_element INTEGER DEFAULT 0,
    resistance_2_elements INTEGER DEFAULT 0,
    resistance_3_elements INTEGER DEFAULT 0,
    fire_resistance INTEGER DEFAULT 0,
    earth_resistance INTEGER DEFAULT 0,
    water_resistance INTEGER DEFAULT 0,
    air_resistance INTEGER DEFAULT 0,
    elemental_resistance INTEGER DEFAULT 0,
    rear_resistance INTEGER DEFAULT 0,
    critical_resistance INTEGER DEFAULT 0,
    armor_given INTEGER DEFAULT 0,
    armor_received INTEGER DEFAULT 0,
    is_shop_item INTEGER DEFAULT FALSE
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS unobtainables (
    item_id INTEGER PRIMARY KEY NOT NULL,
    reason TEXT
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS item_names (
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    en TEXT,
    fr TEXT,
    pt TEXT,
    es TEXT,
    PRIMARY KEY(item_id)
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS item_types (
    item_type INTEGER NOT NULL PRIMARY KEY,
    position TEXT,
    disables_offhand INTEGER DEFAULT FALSE
) STRICT, WITHOUT ROWID ;

CREATE TABLE IF NOT EXISTS item_type_names (
    item_type INTEGER NOT NULL REFERENCES item_types(item_type),
    t_en TEXT,
    t_fr TEXT,
    t_pt TEXT,
    t_es TEXT,
    PRIMARY KEY(item_type)
) STRICT, WITHOUT ROWID ;
"""


keys = [
    "item_id",
    "item_lv",
    "item_rarity",
    "item_type",
    "hp",
    "ap",
    "mp",
    "wp",
    "range",
    "control",
    "block",
    "critical_hit",
    "dodge",
    "lock",
    "force_of_will",
    "rear_mastery",
    "healing_mastery",
    "melee_mastery",
    "distance_mastery",
    "berserk_mastery",
    "critical_mastery",
    "fire_mastery",
    "earth_mastery",
    "water_mastery",
    "air_mastery",
    "mastery_1_element",
    "mastery_2_elements",
    "mastery_3_elements",
    "elemental_mastery",
    "resistance_1_element",
    "resistance_2_elements",
    "resistance_3_elements",
    "fire_resistance",
    "earth_resistance",
    "water_resistance",
    "air_resistance",
    "elemental_resistance",
    "rear_resistance",
    "critical_resistance",
    "armor_given",
    "armor_received",
    "is_shop_item",
]

QUERY = "INSERT INTO ITEMS({}) VALUES({})".format(
    ", ".join(keys),
    ", ".join(f":{k}" for k in keys),
)


if __name__ == "__main__":
    items = object_parsing.EquipableItem.from_bz2_bundled()
    all_item_ids = {i._item_id for i in items}  # pyright: ignore[reportPrivateUsage]

    conn = apsw.Connection("items.db")
    conn.execute(SCHEMA)

    data: list[dict[str, int]] = []

    for item in items:
        d: dict[str, int] = {k: getattr(item, f"_{k}", 0) for k in keys}
        data.append(d)

    conn.executemany(QUERY, data)

    titles = [
        {"item_id": item._item_id, **item._title_strings}
        for item in items  # pyright: ignore[reportPrivateUsage]
    ]

    conn.executemany(
        """
        INSERT INTO item_names (item_id, en, fr, pt, es) VALUES (:item_id, :en, :fr, :pt, :es)
        """,
        titles,
    )

    with open("json_data/blueprints.json", mode="rb") as bp:
        bpdata = json.load(bp)

    with open("json_data/recipeResults.json", mode="rb") as results_are_why_ankama:
        recresults = {i["recipeId"]: i["productedItemId"] for i in json.load(results_are_why_ankama)}

    blueprints: set[int] = set()
    for blueprint in bpdata:
        blueprint_id = blueprint["blueprintId"]
        recipe_ids = blueprint["recipeId"]
        for rid in recipe_ids:
            try:
                actual_id = recresults[rid]
                blueprints.add(actual_id)
            except KeyError as e:
                (k,) = e.args
                if k not in (7165, 7166, 7167):  # known failures
                    raise

    conn.executemany(
        """INSERT INTO blueprints (item_id) VALUES(?)""",
        [(i,) for i in blueprints],
    )

    item_id_regex = re.compile(r"^(\d{1,6})\w?.*$", re.DOTALL)

    for path, table_name in (
        ("../community_sourced_data/ubs.txt", "ub_items"),
        ("../community_sourced_data/pvp.txt", "pvp_items"),
        ("../community_sourced_data/archdrops.txt", "archmonster_items"),
        ("../community_sourced_data/hordes.txt", "horde_items"),
    ):

        item_ids: list[int] = []
        with open(path, encoding="utf-8") as ub_data:
            lines = [stripped for line in ub_data.readlines() if (stripped := line.strip())]
            for line in lines:
                if m := item_id_regex.match(line):
                    item_ids.append(int(m.group(1)))

        conn.executemany(
            f"""INSERT INTO [{table_name}] (item_id) VALUES(?)""",
            [(i,) for i in item_ids],
        )

    with open("json_data/recipes.json", mode="rb") as rcp:
        recipes = json.load(rcp)

    recipes_limited = {
        rid: (rid, recipe["isUpgrade"], recipe["upgradeItemId"])
        for recipe in recipes
        if (rid := recresults.get(recipe["id"])) in all_item_ids
    }

    conn.executemany(
        """
        INSERT INTO
        recipes (item_id, is_upgrade, upgrade_of)
        VALUES (?, ?, ?)
        """,
        list(recipes_limited.values()),
    )

    item_type_data: list[tuple[int, str, bool]] = []
    item_type_name_data: list[dict[str, str]] = []

    for type_id, type_data in ITEM_TYPE_MAP.items():
        position: str = type_data["position"][0]  # type: ignore
        disables: bool = bool(type_data["disables"])
        item_type_data.append((type_id, position, disables))

        loc = {"item_type": type_id, **(type_data["title"])}  # type: ignore
        item_type_name_data.append(loc)  # type: ignore

    conn.executemany(
        """
        INSERT INTO item_types(item_type, position, disables_offhand) VALUES (?,?,?)
        """,
        item_type_data,
    )

    conn.executemany(
        """
        INSERT INTO item_type_names(item_type, t_en, t_fr, t_pt, t_es)
        VALUES (:item_type, :en, :fr, :pt, :es)
        """,
        item_type_name_data,
    )

    conn.executemany(
        """
        INSERT INTO unobtainables (item_id, reason) VALUES (?, ?)
        """,
        list(unobs.get_unobtainable_info()),
    )
