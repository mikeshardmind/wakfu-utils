"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
# pyright: reportPrivateUsage=none
from __future__ import annotations

from typing import Literal

from msgspec import Struct, field, msgpack

from .b2048 import encode as b2048encode
from .restructured_types import ClassesEnum, Priority, SetMinimums, StatPriority, Stats
from .solver import SolveError, solve, v1Config
from .wakforge_buildcodes import Buildv1 as WFBuild

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

_adaptive_tolerance_map: dict[int, int] = {
    20: 20,
    35: 35,
    50: 50,
    65: 30,
    80: 30,
    95: 30,
    110: 30,
    125: 15,
    140: 15,
    155: 15,
    170: 15,
    185: 15,
    200: 15,
    215: 15,
    230: 15,
}

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
        bcrit=stats.crit - 3,  # wakforge is doing something wrong here, won't be fixes for this entrypoint
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
        hard_cap_depth=25,
        tolerance=_adaptive_tolerance_map.get(lv, 15),
        search_depth=3 if dry_run else 1,
    )

    try:
        result = solve(cfg, ignore_missing_items=True)
        best = result[0]
    except (IndexError, SolveError):
        return (None, "No possible solution found")

    _score, items = best
    item_ids = [i._item_id for i in items]  # pyright: ignore
    return (item_ids, None)


class v2Config(Struct):
    allowed_rarities: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    target_stats: SetMinimums = field(default_factory=SetMinimums)
    dry_run: bool = False
    objectives: StatPriority = field(default_factory=StatPriority)
    forbidden_items: list[int] = field(default_factory=list)


class v2Result(Struct):
    build_code: str | None = None
    error_code: str | None = None
    item_ids: list[int] = field(default_factory=list)
    debug_info: str | None = None


def partial_solve_v2(
    *,
    build_code: str,
    config: v2Config,
) -> v2Result:
    # This may look redundant, but it's exceptionally cheap validation
    try:
        config = msgpack.decode(msgpack.encode(config), type=v2Config)
    except Exception as exc:  # noqa: BLE001
        msg = (exc.__class__.__name__, *map(str, exc.args))
        p = b2048encode(msgpack.encode(msg))
        return v2Result(None, "Invalid config", debug_info=p)

    if not config.objectives.is_valid:
        msg = ("objectives", config.objectives)
        p = b2048encode(msgpack.encode(msg))
        return v2Result(None, "Invalid config", debug_info=p)

    build = WFBuild.from_code(build_code)
    stats = build.get_allocated_stats().to_stat_values(build.classenum)
    if build.classenum is ClassesEnum.Ecaflip:
        stats = stats + Stats(crit=20)
    item_ids = [i.item_id for i in build.get_items() if i.item_id > 0]
    ap = config.target_stats.ap - stats.ap
    mp = config.target_stats.mp - stats.mp
    wp = config.target_stats.wp - stats.wp
    ra = config.target_stats.ra - stats.ra

    forbidden_rarities = [i for i in range(1, 8) if i not in config.allowed_rarities]

    # TODO: modify internals to not need this level of wrapping

    lookup: dict[Priority, Literal["full", "half", "none"]] = {
        Priority.full_negative_only: "full",
        Priority.half_negative_only: "half",
    }

    cfg = v1Config(
        lv=build.level,
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
        num_mastery=config.objectives.elements.bit_count(),
        forbid_rarity=forbidden_rarities,
        idforce=item_ids,
        dist=config.objectives.distance_mastery == Priority.prioritized,
        melee=config.objectives.melee_mastery == Priority.prioritized,
        heal=config.objectives.heal_mastery == Priority.prioritized,
        zerk=config.objectives.berserk_mastery == Priority.prioritized,
        rear=config.objectives.rear_mastery == Priority.prioritized,
        negrear=lookup.get(config.objectives.rear_mastery, "none"),
        negzerk=lookup.get(config.objectives.berserk_mastery, "none"),
        dry_run=config.dry_run,
        hard_cap_depth=25,
        tolerance=_adaptive_tolerance_map.get(build.level, 15),
        search_depth=3 if config.dry_run else 1,
        elements=config.objectives.elements,
    )

    try:
        result = solve(cfg, ignore_missing_items=True)
        best = result[0]
    except (IndexError, SolveError):
        return v2Result(None, "No possible solution found", debug_info=None)
    except Exception as exc:  # noqa: BLE001
        msg = (exc.__class__.__name__, *map(str, exc.args))
        p = b2048encode(msgpack.encode(msg))
        return v2Result(None, "Unknown error, see debug info", debug_info=p)

    score, found_items = best

    found_item_ids = [i._item_id for i in found_items]

    if config.dry_run:
        return v2Result(None, None, found_item_ids, None)

    ecount = config.objectives.elements.bit_count()
    for item in found_items:
        if item._item_id not in item_ids:
            try:
                if getattr(item, f"_mastery_{ecount}_elements", 0):
                    build.add_item(item, config.objectives.elements)
                else:
                    build.add_item(item)
            except RuntimeError as exc:
                msg = (exc.__class__.__name__, *map(str, exc.args))
                p = b2048encode(msgpack.encode(msg))
                return v2Result(None, "Unknown error, see debug info", debug_info=p)

    debug_info = b2048encode(msgpack.encode({"sc": score}))

    return v2Result(build.to_code(), None, found_item_ids, debug_info=debug_info)
