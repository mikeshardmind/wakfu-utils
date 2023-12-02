"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""  # noqa: INP001
from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, LiteralString

import apsw
from numpy import add

from wakautosolver.restructured_types import DUMMY_MIN, SetMinimums, Stats
from wakautosolver.wakforge_buildcodes import v1BuildSlotsOrder

path = Path(__file__).with_name("data") / "items.db"


FORMATTABLE_QUERY = """
SELECT DISTINCT {columns} FROM items NATURAL JOIN item_types
WHERE item_lv >= :min_lv
    AND item_lv <= :max_lv
    AND item_rarity in ({rarities})
    AND position = :position
"""

def format_query(stats: list[LiteralString], rarities: list[int]) -> LiteralString:
    """ Currently expected to only ever be [ap, mp, wp, range] """
    cols = ", ".join(f"[{column}]" for column in stats)
    safe_rarities = ("1", "2", "3", "4" ,"5" ,"6" ,"7")
    raritiy_str: LiteralString = ", ".join(r for r in safe_rarities if int(r) in rarities)
    return FORMATTABLE_QUERY.format(columns=cols, rarities=raritiy_str)


def stat_wheeling(
    stat_mins: SetMinimums, available_slots: list[str], allowed_rarities: list[int], min_lv: int, max_lv: int
) -> dict[str, list[tuple[int]]]:
    ret: dict[str, list[tuple[int]]] = {}
    if not available_slots:
        return ret

    allowed: list[LiteralString] = ["ap", "mp", "wp", "ra"]

    cols: list[LiteralString] = [s for s in allowed if getattr(stat_mins, s, DUMMY_MIN) > DUMMY_MIN]

    conn = apsw.Connection(str(path), flags=apsw.SQLITE_OPEN_READONLY)

    cursor = conn.cursor()

    with conn:
        for s in set(available_slots):
            ret[s] = list(cursor.execute(format_query(cols, allowed_rarities), {"min_lv": min_lv, "max_lv": max_lv, "position": s}))

    return ret


AllowedStatType = Literal["ap", "mp", "wp", "ra"]

def all_valid_by_slot(
    stat_mins: SetMinimums, available_slots: list[str], allowed_rarities: list[int], min_lv: int, max_lv: int
) -> Iterator[tuple[str, tuple[int]]]:

    allowed: list[AllowedStatType] = ["ap", "mp", "wp", "ra"]
    cols: list[AllowedStatType] = [s for s in allowed if getattr(stat_mins, s, DUMMY_MIN) > DUMMY_MIN]
    data = stat_wheeling(stat_mins=stat_mins, available_slots=available_slots, allowed_rarities=allowed_rarities, min_lv=min_lv, max_lv=max_lv)

    for combo in itertools.product(*[data[k] for k in available_slots]):

        elem_wise_sum = add.reduce(combo)

        temp: dict[AllowedStatType, int] = {k: v for k, v in zip(cols, elem_wise_sum)}  # noqa: C416

        s = Stats(**temp)

        if stat_mins.stats_met(s):
            yield from zip(available_slots, combo)


if __name__ == "__main__":
    """ This will take an impossibly long time to run for just a single scenario limited to only these stats """
    s: dict[str, set[tuple[int, ...]]] = defaultdict(set)
    for slot, stats in all_valid_by_slot(SetMinimums(ap=12, mp=6, wp=0, ra=0), v1BuildSlotsOrder, [1,2,3,4,5,6,7], 1, 230):
        s[slot].add(stats)
    print(s)  # noqa: T201
