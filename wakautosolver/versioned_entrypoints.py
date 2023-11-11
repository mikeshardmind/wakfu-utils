"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from typing import Literal

from .restructured_types import SetMinimums, Stats
from .solver import SolveError, solve, v1Config

ClassNames = Literal[
    "Feca",
    "Osa",
    "Enu",
    "Sram",
    "Xel",
    "Eca",
    "Eni",
    "Iop",
    "Cra",
    "Sadi",
    "Sac",
    "Panda",
    "Rogue",
    "Masq",
    "Ougi",
    "Fog",
    "Elio",
    "Hupper",
]

v1Result = tuple[list[int] | None, str | None]


def partial_solve_v1(
    *,
    lv: int,
    stats: Stats,
    target_stats: SetMinimums,
    equipped_items: list[int],
    num_mastery: int,
    allowed_rarities: list[int],
    dist: bool = False,
    melee: bool = False,
    heal: bool = False,
    zerk: bool = False,
    rear: bool = False,
    dry_run: bool = False,
) -> v1Result:
    """
    Doesn't handle sublimations, passives, etc yet

    Use from pyodide:

    // passing in other values besides the below
    // may cause problems with solve quality for v1
    let targets = SetMinimum.callKwargs({ap: 12, mp: 6, ra: 2, wp: 0});


    // for the full list of supported Stats, see Stats class
    let stats = Stats.callKwargs({ap: 7, mp: 4, ...});

    let [result, error] = partial_solve_v1.callKwargs(
        {
        stats: stats,
        target_stats: targets,
        }
    )
    """

    ap = target_stats.ap - stats.ap
    mp = target_stats.mp - stats.mp
    ra = target_stats.ra - stats.ra
    wp = target_stats.wp - stats.wp

    forbidden_rarities = [i for i in range(1, 8) if i not in allowed_rarities]

    equipped = [i for i in equipped_items if i] if equipped_items else []

    cfg = v1Config(
        lv=lv,
        ap=ap,
        mp=mp,
        wp=wp,
        ra=ra,
        baseap=stats.ap,
        basemp=stats.mp,
        basera=stats.ra,
        bawewp=stats.wp,
        bcrit=stats.crit,
        bcmast=stats.crit_mastery,
        bmast=stats.elemental_mastery,
        num_mastery=num_mastery,
        forbid_rarity=forbidden_rarities,
        idforce=equipped,
        dist=dist,
        melee=melee,
        heal=heal,
        zerk=zerk,
        rear=rear,
        dry_run=dry_run,
        hard_cap_depth=50,
        tolerance=30,
        search_depth=2,
    )

    try:
        result = solve(cfg, ignore_missing_items=True)
        best = result[0]
    except (IndexError, SolveError):
        return (None, "No possible solution found")

    _score, items = best
    item_ids = [i._item_id for i in items]  # pyright: ignore
    return (item_ids, None)
