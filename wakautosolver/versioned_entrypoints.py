"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import enum
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Literal

from . import __version__
from .restructured_types import (
    DUMMY_MAX,
    DUMMY_MIN,
    ClassElements,
    ElementsEnum,
    Priority,
    StatPriority,
    load_item_source_data,
)
from .restructured_types import SetMaximums as RealSetMaxs
from .restructured_types import SetMinimums as RealSetMins
from .solver import ImpossibleStatError, SolveError, solve, v1Config
from .wakforge_buildcodes import Buildv1 as WFBuild
from .wakforge_buildcodes import build_to_code

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
    65: 60,
    80: 60,
    95: 60,
    110: 60,
    125: 30,
    140: 30,
    155: 30,
    170: 30,
    185: 30,
    200: 15,
    215: 15,
    230: 14,
    245: 15,
}

v1Result = tuple[list[int] | None, str | None]


# Exists because versioning
@dataclass(unsafe_hash=True)
class SetMinimums:
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


@dataclass(unsafe_hash=True)
class SetMaximums:
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


class SolveType(enum.IntEnum):
    OPTIMIZE = 1
    QUICK = 2
    FIRST_MATCH = 3


@dataclass
class v2Config:
    allowed_rarities: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    target_stats: SetMinimums = field(default_factory=SetMinimums)
    dry_run: bool = False
    objectives: StatPriority = field(default_factory=StatPriority)
    forbidden_items: list[int] = field(default_factory=list)
    ignore_existing_items: bool = False
    forbidden_sources: list[
        Literal["arch", "horde", "pvp", "ultimate_boss", "blueprints"]
    ] = field(default_factory=list)
    stats_maxs: SetMaximums = field(default_factory=SetMaximums)
    enable_testing_features: bool = False
    solve_type: SolveType = SolveType.OPTIMIZE


v3Config = v2Config


@dataclass
class v2Result:
    build_code: str | None = None
    error_code: str | None = None
    item_ids: list[int] = field(default_factory=list)
    debug_info: str | None = None


def partial_solve_v2(
    *,
    build_code: str,
    config: v2Config,
    progress_callback: Callable[[int, int], None] | None = None,
    lwx: bool = False,
    unravel: bool = False,
) -> v2Result:
    # pyodide proxies aren't actually lists...
    config.allowed_rarities = [i for i in config.allowed_rarities if i]
    config.forbidden_items = [i for i in config.forbidden_items if i]
    config.forbidden_sources = [s for s in config.forbidden_sources if s]

    # and enums...
    config.objectives._pyodide_norm()  # pyright: ignore[reportPrivateUsage]
    target_stats = config.target_stats.to_real()

    item_sources = load_item_source_data()
    forbidden_ids: set[int] = set()
    for source in config.forbidden_sources:
        forbidden_ids |= getattr(item_sources, source)

    allowed_sources = [
        s
        for s in ("arch", "horde", "pvp", "ultimate_boss")
        if s not in config.forbidden_sources
    ]  # The only blueprint that overlaps another category is tal-kasha's broadsowrd.
    # This is not to be unexcluded right now, as the recipe also is ub dependent.

    for source in allowed_sources:  # in case of multiple sources
        forbidden_ids -= getattr(item_sources, source)

    forbidden_ids -= item_sources.non_finite_arch_horde
    config.forbidden_items.extend(forbidden_ids)

    if not config.objectives.is_valid:
        msg = ("objectives", config.objectives)
        return v2Result(
            None, "Invalid config (get debug info if opening an issue)", debug_info=None
        )

    build = WFBuild.from_code(build_code)
    sublimations = build.get_sublimations()  # TODO: consider this + below line
    if config.ignore_existing_items:
        build.clear_items()
    point_spread = build.get_allocated_stats()
    stats = point_spread.to_stat_values(build.classenum)
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
        wakfu_class=build.classenum,
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
        idforbid=[i for i in config.forbidden_items if i],
        dist=config.objectives.distance_mastery == Priority.prioritized,
        melee=config.objectives.melee_mastery == Priority.prioritized,
        heal=config.objectives.heal_mastery == Priority.prioritized,
        zerk=config.objectives.berserk_mastery == Priority.prioritized,
        rear=config.objectives.rear_mastery == Priority.prioritized,
        negrear=lookup.get(config.objectives.rear_mastery, "none"),
        negzerk=lookup.get(config.objectives.berserk_mastery, "none"),
        dry_run=config.dry_run,
        hard_cap_depth=50,
        tolerance=_adaptive_tolerance_map.get(build.level, 14),
        search_depth=1,
        elements=config.objectives.elements,
        lwx=lwx,
        unraveling=unravel,
    )

    try:
        result = solve(
            cfg,
            progress_callback=progress_callback,
            point_spread=point_spread,
            passives=build.get_passives(),
            sublimations=sublimations,
        )
        best = result[0]
    except ImpossibleStatError as exc:
        return v2Result(None, exc.args[0], debug_info=None)
    except (IndexError, SolveError):
        return v2Result(None, "No possible solution found", debug_info=None)
    except Exception as exc:  # noqa: BLE001
        msg = "\n".join(traceback.format_exception(exc))
        return v2Result(None, "Unknown error, see debug info", debug_info=msg)

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
            msg = "".join((__version__, "\n\n", *traceback.format_exception(exc)))
            return v2Result(None, "Unknown error, see debug info", debug_info=msg)

    debug_info = repr({"score": score})

    return v2Result(build_to_code(build), None, found_item_ids, debug_info=debug_info)
