"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from typing import Literal

from .build_codes import Build, ClassName, Item, encode_build
from .build_codes import Stats as AssignedStatPoints
from .restructured_types import Priority, SetMinimums, StatPriority, Stats
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
        tolerance=15,
        search_depth=1,
    )

    try:
        result = solve(cfg, ignore_missing_items=True)
        best = result[0]
    except (IndexError, SolveError):
        return (None, "No possible solution found")

    _score, items = best
    item_ids = [i._item_id for i in items]  # pyright: ignore
    return (item_ids, None)


v2SuccesfulResult = tuple[float, str, list[int]]
v2Result = tuple[v2SuccesfulResult | None, str | None]


def partial_solve_v2(
    *,
    lv: int,
    classname: ClassNames,
    stats: AssignedStatPoints,
    target_stats: SetMinimums,
    equipped_items: list[int],
    allowed_rarities: list[int],
    solve_objectives: StatPriority,
    dry_run: bool = False,
) -> v2Result:
    cl = ClassName[classname]
    base_stats = stats.to_stat_values(is_xelor=cl == ClassName.Xelor)
    forbidden_rarities = [i for i in range(1, 8) if i not in allowed_rarities]
    equipped = [i for i in equipped_items if i] if equipped_items else []

    # TODO: refactor solve to not need the math done here
    ap = target_stats.ap - base_stats.ap
    mp = target_stats.mp - base_stats.mp
    ra = target_stats.ra - base_stats.ra
    wp = target_stats.wp - base_stats.wp

    lk: dict[Priority, Literal["full", "half", "none"]] = {
        Priority.half_negative_only: "half",
        Priority.full_negative_only: "full",
    }
    negrear = lk.get(solve_objectives.rear_mastery, "none")
    negzerk = lk.get(solve_objectives.berserk_mastery, "none")

    cfg = v1Config(
        lv=lv,
        ap=ap,
        mp=mp,
        wp=wp,
        ra=ra,
        baseap=base_stats.ap,
        basemp=base_stats.mp,
        basera=base_stats.ra,
        bawewp=base_stats.wp,
        bcrit=base_stats.crit,
        bcmast=base_stats.crit_mastery,
        bmast=base_stats.elemental_mastery,
        num_mastery=solve_objectives.number_of_elements,
        forbid_rarity=forbidden_rarities,
        idforce=equipped,
        dist=solve_objectives.distance_mastery == Priority.prioritized,
        melee=solve_objectives.melee_mastery == Priority.prioritized,
        heal=solve_objectives.heal_mastery == Priority.prioritized,
        zerk=solve_objectives.berserk_mastery == Priority.prioritized,
        rear=solve_objectives.rear_mastery == Priority.prioritized,
        dry_run=dry_run,
        hard_cap_depth=50,
        tolerance=15,
        search_depth=1,
        negrear=negrear,
        negzerk=negzerk,
    )

    try:
        result = solve(cfg, ignore_missing_items=True)
        best = result[0]
    except (IndexError, SolveError):
        return (None, "No possible solution found")

    score, items = best
    item_ids = [i._item_id for i in items]  # pyright: ignore

    build = Build(
        cl,
        level=lv,
        stats=stats,
        items=[Item(i) for i in item_ids],
    )

    encoded = encode_build(build)

    return (score, encoded, item_ids), None


# TODO: Just take in a build object + objectives & weights for next iteration
