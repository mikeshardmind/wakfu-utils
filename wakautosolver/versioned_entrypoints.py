"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import traceback
import zlib
from collections.abc import Callable
from typing import Literal

from msgspec import Struct, field, msgpack
from msgspec.structs import asdict

from .b2048 import encode as b2048encode
from .object_parsing import load_item_source_data
from .restructured_types import DUMMY_MAX, DUMMY_MIN, ClassElements, ClassesEnum, ElementsEnum, Priority, StatPriority, Stats
from .restructured_types import SetMaximums as RealSetMaxs
from .restructured_types import SetMinimums as RealSetMins
from .solver import ImpossibleStatError, SolveError, solve, v1Config
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
    200: 14,
    215: 15,
    230: 14,
}

v1Result = tuple[list[int] | None, str | None]


# Exists because versioning
class SetMinimums(Struct, frozen=True, gc=True):
    ap: int = DUMMY_MIN
    mp: int = DUMMY_MIN
    wp: int = DUMMY_MIN
    ra: int = DUMMY_MIN
    crit: int = DUMMY_MIN
    crit_mastery: int = DUMMY_MIN
    elemental_mastery: int = DUMMY_MIN
    one_element_mastery: int = DUMMY_MIN
    two_element_mastery: int = DUMMY_MIN
    three_element_mastery: int = DUMMY_MIN
    distance_mastery: int = DUMMY_MIN
    rear_mastery: int = DUMMY_MIN
    heal_mastery: int = DUMMY_MIN
    beserk_mastery: int = DUMMY_MIN
    melee_mastery: int = DUMMY_MIN
    control: int = DUMMY_MIN
    block: int = DUMMY_MIN
    fd: int = DUMMY_MIN
    heals_performed: int = DUMMY_MIN
    lock: int = DUMMY_MIN
    dodge: int = DUMMY_MIN
    armor_given: int = DUMMY_MIN

    def to_real(self) -> RealSetMins:
        data = asdict(self)
        for new, old in (
            ("critical_hit", "crit"),
            ("critical_mastery", "crit_mastery"),
            ("mastery_3_elements", "three_element_mastery"),
            ("mastery_2_elements", "two_element_mastery"),
            ("mastery_1_element", "one_element_mastery"),
            ("healing_mastery", "heal_mastery"),
            ("berserk_mastery", "beserk_mastery"),
        ):
            data[new] = data.pop(old)

        return RealSetMins(**data)


class SetMaximums(Struct, frozen=True, gc=True):
    ap: int = DUMMY_MAX
    mp: int = DUMMY_MAX
    wp: int = DUMMY_MAX
    ra: int = DUMMY_MAX
    crit: int = DUMMY_MAX
    crit_mastery: int = DUMMY_MAX
    elemental_mastery: int = DUMMY_MAX
    one_element_mastery: int = DUMMY_MAX
    two_element_mastery: int = DUMMY_MAX
    three_element_mastery: int = DUMMY_MAX
    distance_mastery: int = DUMMY_MAX
    rear_mastery: int = DUMMY_MAX
    heal_mastery: int = DUMMY_MAX
    beserk_mastery: int = DUMMY_MAX
    melee_mastery: int = DUMMY_MAX
    control: int = DUMMY_MAX
    block: int = DUMMY_MAX
    fd: int = DUMMY_MAX
    heals_performed: int = DUMMY_MAX
    lock: int = DUMMY_MAX
    dodge: int = DUMMY_MAX
    armor_given: int = DUMMY_MAX

    def to_real(self) -> RealSetMaxs:
        data = asdict(self)
        for new, old in (
            ("critical_hit", "crit"),
            ("critical_mastery", "crit_mastery"),
            ("mastery_3_elements", "three_element_mastery"),
            ("mastery_2_elements", "two_element_mastery"),
            ("mastery_1_element", "one_element_mastery"),
            ("healing_mastery", "heal_mastery"),
            ("berserk_mastery", "beserk_mastery"),
        ):
            data[new] = data.pop(old)

        return RealSetMaxs(**data)


def partial_solve_v1(
    *,
    lv: int,
    stats: Stats,
    target_stats: RealSetMins,
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
        bcrit=stats.critical_hit - 3,  # wakforge is doing something wrong here, won't be fixes for this entrypoint
        bcmast=stats.critical_mastery,
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
        hard_cap_depth=15,
        tolerance=_adaptive_tolerance_map.get(lv, 14),
        search_depth=1 if dry_run else 1,
    )

    try:
        result = solve(cfg)
        best = result[0]
    except (IndexError, SolveError):
        return (None, "No possible solution found")

    _score, items = best
    item_ids = [i.item_id for i in items]
    return (item_ids, None)


class v2Config(Struct):
    allowed_rarities: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    target_stats: SetMinimums = field(default_factory=SetMinimums)
    dry_run: bool = False
    objectives: StatPriority = field(default_factory=StatPriority)
    forbidden_items: list[int] = field(default_factory=list)
    ignore_existing_items: bool = False
    forbidden_sources: list[Literal["arch", "horde", "pvp", "ultimate_boss"]] = field(default_factory=list)
    stats_maxs: SetMaximums = field(default_factory=SetMaximums)


class v2Result(Struct):
    build_code: str | None = None
    error_code: str | None = None
    item_ids: list[int] = field(default_factory=list)
    debug_info: str | None = None


def compressed_encode(obj: object) -> str:
    return b2048encode(zlib.compress(msgpack.encode(obj), level=9, wbits=-15))


def partial_solve_v2(
    *,
    build_code: str,
    config: v2Config,
    progress_callback: Callable[[int, int], None] | None = None,
) -> v2Result:
    # pyodide proxies aren't actually lists...
    config.allowed_rarities = [i for i in config.allowed_rarities if i]
    config.forbidden_items = [i for i in config.forbidden_items if i]
    config.forbidden_sources = [s for s in config.forbidden_sources if s]
    # This may look redundant, but it's exceptionally cheap validation
    try:
        config = msgpack.decode(msgpack.encode(config), type=v2Config)
    except Exception as exc:  # noqa: BLE001
        msg = traceback.format_exception(exc)
        return v2Result(None, "Invalid config (get debug info if opening an issue)", debug_info=compressed_encode(msg))

    target_stats = config.target_stats.to_real()

    item_sources = load_item_source_data()
    forbidden_ids: set[int] = set()
    for source in config.forbidden_sources:
        forbidden_ids |= getattr(item_sources, source)
    forbidden_ids -= item_sources.non_finite_arch_horde
    config.forbidden_items.extend(forbidden_ids)

    if not config.objectives.is_valid:
        msg = ("objectives", config.objectives)
        return v2Result(None, "Invalid config (get debug info if opening an issue)", debug_info=compressed_encode(msg))

    build = WFBuild.from_code(build_code)
    if config.ignore_existing_items:
        build.clear_items()
    stats = build.get_allocated_stats().to_stat_values(build.classenum)
    item_ids = [i.item_id for i in build.get_items() if i.item_id > 0]
    ap = target_stats.ap - stats.ap
    mp = target_stats.mp - stats.mp
    wp = target_stats.wp - stats.wp
    ra = target_stats.ra - stats.ra

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
        stat_minimums=target_stats,
        stat_maximums=config.stats_maxs.to_real(),
        base_stats=stats,
        baseap=stats.ap,
        basemp=stats.mp,
        basera=stats.ra,
        bawewp=stats.wp,
        bcrit=stats.critical_hit,
        bcmast=stats.critical_mastery,
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
        hard_cap_depth=35,
        tolerance=_adaptive_tolerance_map.get(build.level, 14),
        search_depth=1,
        elements=config.objectives.elements,
    )

    try:
        result = solve(cfg, progress_callback=progress_callback)
        best = result[0]
    except ImpossibleStatError as exc:
        return v2Result(None, exc.args[0], debug_info=None)
    except (IndexError, SolveError):
        return v2Result(None, "No possible solution found", debug_info=None)
    except Exception as exc:  # noqa: BLE001
        msg = traceback.format_exception(exc)
        return v2Result(None, "Unknown error, see debug info", debug_info=compressed_encode(msg))

    score, found_items = best

    found_item_ids = [i.item_id for i in found_items]

    if config.dry_run:
        return v2Result(None, None, found_item_ids, None)

    ecount = config.objectives.elements.bit_count()
    remaining_elements = [e for e in ElementsEnum if e not in config.objectives.elements]
    remaining_elements.sort(key=ClassElements[build.classenum].__contains__, reverse=True)

    for item in found_items:
        num_random = item.num_random_mastery
        elements = config.objectives.elements if num_random else ElementsEnum.empty

        for e in remaining_elements[: num_random - ecount]:
            elements |= e
        try:
            if item.item_id in item_ids:
                build.add_elements_to_item(item.item_id, elements)
            else:
                build.add_item(item, elements)
        except RuntimeError as exc:
            msg = traceback.format_exception(exc)
            return v2Result(None, "Unknown error, see debug info", debug_info=compressed_encode(msg))

    debug_info = compressed_encode({"score": score})

    return v2Result(build.to_code(), None, found_item_ids, debug_info=debug_info)
