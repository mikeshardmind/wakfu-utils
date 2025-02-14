"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import collections
import itertools
import logging
import statistics
import sys
from collections.abc import Callable, Hashable, Iterable
from dataclasses import astuple
from functools import lru_cache, reduce
from operator import add, and_, attrgetter, itemgetter
from typing import Final, Protocol, TypeVar

from ._build_codes import Stats as StatSpread
from .item_conditions import get_item_conditions
from .object_parsing import EquipableItem, get_all_items, load_item_source_data, set_locale
from .restructured_types import ClassesEnum, ElementsEnum, SetMaximums, SetMinimums, Stats, apply_w2h, v1Config


T = TypeVar("T")


log = logging.getLogger("solver")


T_contra = TypeVar("T_contra", contravariant=True)


class SupportsWrite(Protocol[T_contra]):
    def write(self, s: T_contra, /) -> object: ...


ALWAYS_SIMMED = "ap", "mp", "ra", "wp" , #"critical_hit", "critical_mastery"
AS_ATTR_GETTER = attrgetter(*ALWAYS_SIMMED)


def setup_logging(output: SupportsWrite[str]) -> None:
    handler = logging.StreamHandler(output)
    formatter = logging.Formatter("%(message)s", datefmt="%Y-%m-%d %H:%M:%S", style="%")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def ordered_keep_by_key(it: Iterable[T], key: Callable[[T], Hashable], k: int = 1) -> list[T]:
    seen_counts: collections.Counter[Hashable] = collections.Counter()
    ret: list[T] = []
    for i in it:
        _key = key(i)
        seen_counts[_key] += 1
        if seen_counts[_key] <= k:
            ret.append(i)
    return ret


def inplace_ordered_keep_by_key(it: list[T], key: Callable[[T], Hashable], k: int = 1) -> None:
    uniq = ordered_keep_by_key(it, key, k)
    for v in it[::-1]:
        if v not in uniq:
            it.remove(v)


class SolveError(Exception):
    pass


class ImpossibleStatError(SolveError):
    pass


def solve(
    ns: v1Config,
    progress_callback: Callable[[int, int], None] | None = None,
    point_spread: StatSpread | None = None,
    passives: list[int] | None = None,
    sublimations: list[int] | None = None,
) -> list[tuple[float, list[EquipableItem]]]:
    """Still has some debug stuff in here, will be refactoring this all later."""

    set_locale(ns.locale)

    # ## Everything in this needs abstracting into something
    # that can handle user input and be more dynamic.
    # ## Could benefit from some optimizations here and there.

    ALL_OBJS = get_all_items()

    allowed_rarities = ns.allowed_rarities or list(range(1, 8))
    if ns.forbid_rarity:
        allowed_rarities = [i for i in allowed_rarities if i not in ns.forbid_rarity]

    LOW_BOUND = max(ns.lv - ns.tolerance, 1)

    def _score_key(item: EquipableItem | Stats | None) -> float:
        score = 0.0
        if not item:
            return score

        elemental_modifier = 1.2 if ns.wakfu_class == ClassesEnum.Huppermage else 1

        score += item.elemental_mastery * elemental_modifier
        if ns.melee:
            score += item.melee_mastery
        if ns.dist:
            score += item.distance_mastery
        if ns.zerk and ns.negzerk not in ("half", "full"):
            score += item.berserk_mastery
        else:
            if item.berserk_mastery < 0:
                if ns.negzerk == "full":
                    mul = 1.0
                elif ns.negzerk == "half":
                    mul = 0.5
                else:
                    mul = 0.0

                score += item.berserk_mastery * mul

        if ns.rear and ns.negrear not in ("full", "half"):
            score += item.rear_mastery
        else:
            if item.rear_mastery < 0:
                if ns.negrear == "full":
                    mul = 1.0
                elif ns.negrear == "half":
                    mul = 0.5
                else:
                    mul = 0.0

                score += item.rear_mastery * mul

        if ns.heal:
            score += item.healing_mastery

        if ns.num_mastery == 1:
            score += item.mastery_1_element * elemental_modifier
        if ns.num_mastery <= 2:
            score += item.mastery_2_elements * elemental_modifier
        if ns.num_mastery <= 3:
            score += item.mastery_3_elements * elemental_modifier

        # This isn't perfect, Doziak epps are weird.
        if (n := ns.elements.bit_count()) and not isinstance(item, Stats):
            element_vals = 0
            if ElementsEnum.air in ns.elements:
                element_vals += item.air_mastery
            if ElementsEnum.earth in ns.elements:
                element_vals += item.earth_mastery
            if ElementsEnum.water in ns.elements:
                element_vals += item.water_mastery
            if ElementsEnum.fire in ns.elements:
                element_vals += item.fire_mastery
            score += element_vals / n * elemental_modifier

        return score

    score_key = lru_cache(512)(_score_key)

    @lru_cache(512)
    def crit_score_key(item: EquipableItem | None) -> float:
        if item is None:
            return 0
        base_score = score_key(item)
        return base_score + ((item.critical_hit + base_stats.critical_hit) / 80) * base_score

    @lru_cache(None)
    def has_currently_unhandled_item_condition(item: EquipableItem) -> bool:
        return any(i.unhandled() for i in get_item_conditions(item) if i)

    #    │ 26494   │ Amakna Sword  │
    #    │ 26495   │ Sufokia Sword │
    #    │ 26496   │ Bonta Sword   │
    #    │ 26497   │ Brakmar Sword │
    #    │ 26575   │ Amakna Ring   │
    #    │ 26576   │ Sufokia Ring  │
    #    │ 26577   │ Bonta Ring    │
    #    │ 26578   │ Brakmar Ring  │

    #: don't modify this list without keeping the indices aligned so that sword_id+4=same nation ring id
    # or without modifying uses
    NATION_RELIC_EPIC_IDS = [26494, 26495, 26496, 26497, 26575, 26576, 26577, 26578]

    FORBIDDEN: list[int] = []

    if ns and ns.idforbid:
        FORBIDDEN.extend(ns.idforbid)

    # locale based, only works if user is naming it in locale used and case sensitive currently.
    FORBIDDEN_NAMES: list[str] = ns.forbid if (ns and ns.forbid) else []

    stat_mins = ns.stat_minimums if ns.stat_minimums else SetMinimums(ap=ns.ap, mp=ns.mp, wp=ns.wp, ra=ns.ra)
    stat_maxs = ns.stat_maximums if ns.stat_maximums else SetMaximums()
    base_stats = ns.base_stats or Stats(
        ns.baseap,
        mp=ns.basemp,
        ra=ns.basera,
        wp=ns.bawewp,
        critical_hit=ns.bcrit,
        critical_mastery=ns.bcmast,
        elemental_mastery=ns.bmast,
    )

    influence_level = 0
    if sublimations:
        for sublimation in sublimations:
            match sublimation:
                case 28871:
                    influence_level += 1
                case 27152:
                    influence_level += 2
                case 28872:
                    influence_level += 3
                case 24132:
                    ns.unraveling = True
                case 27186:
                    ns.twoh = True
                case _:
                    pass

    base_stats += Stats(critical_hit=3 * min(influence_level, 6))

    # STAT MODIFYING PASSIVES
    # Things that unconditionally, and without regard for other stats, modify
    # stat quantities (ie. xelor's memory passive)

    if passives:
        if 20003 in passives:  # Motivation
            base_stats += Stats(ap=1, fd=-0.2)
        if 20006 in passives:  # Carnage
            if ns.lv >= 175:
                base_stats += Stats(fd=0.15)
            elif ns.lv >= 75:
                base_stats += Stats(fd=0.10)

    if ns.wakfu_class == ClassesEnum.Xelor and passives and 756 in passives:  # Memory
        base_stats += Stats(wp=6, mp=-2)

    # An interesting query
    # ┌───────────────────────┬────┬────┬────┬────┬──────────────┬───────────────────────────────────┐
    # | Item name (en)        │ ap │ mp │ wp │ ra │   position   │ first ALS bracket combo available │
    # │ Gobball Amulet        │ 1  │ 0  │ 0  │ 0  │ NECK         │ 20                                │
    # │ Gobball Cape          │ 1  │ 0  │ 0  │ 0  │ BACK         │ 20                                │
    # │ Kapow Thongs          │ 0  │ 1  │ 0  │ 0  │ LEGS         │ 50                                │
    # │ Magmacrak Breastplate │ 0  │ 1  │ 0  │ 0  │ CHEST        │ 50                                │
    # │ Conquered Raziel      │ 1  │ 0  │ 0  │ 0  │ FIRST_WEAPON │ 50                                │
    # │ Gufet'Helm            │ 0  │ 1  │ 0  │ 1  │ HEAD         │ 230                               │
    # └───────────────────────┴────┴────┴────┴────┴──────────────┴───────────────────────────────────┘

    common_ap_mp_sum_gt_0 = {
        "BACK": 20,
        "NECK": 20,
        "FIRST_WEAPON": 50,
        "CHEST": 50,
        "LEGS": 50,
    }

    def item_condition_conflicts_requested_stats(item: EquipableItem) -> bool:
        _mins, maxs = get_item_conditions(item)
        if not maxs:
            return False
        return any(smin > smax for smin, smax in zip(*map(astuple, (stat_mins, maxs))))

    def level_filter(item: EquipableItem) -> bool:
        if item.item_slot in ("MOUNT", "PET"):
            return True
        return ns.lv >= item.item_lv >= LOW_BOUND

    def relic_epic_level_filter(item: EquipableItem) -> bool:
        """Special allowances for 3 epic rings to be used slightly longer"""
        if item.item_id == 9723:  # gelano
            return 140 >= ns.lv >= 65
        if item.item_id == 27281:  # bagus shushu
            return 185 >= ns.lv >= 125
        if item.item_id == 27814:
            return 230 >= ns.lv >= 215  # Mopy King Gloves
        return ns.lv >= item.item_lv >= LOW_BOUND

    def minus_relicepic(item: EquipableItem) -> bool:
        return not (item.is_epic or item.is_relic)

    forced_slots: collections.Counter[str] = collections.Counter()
    original_forced_counts: collections.Counter[str] = collections.Counter()
    if ns and (ns.idforce or ns.nameforce):
        _fids = ns.idforce or ()
        _fns = ns.nameforce or ()

        forced_items = [i for i in ALL_OBJS if i.item_id in _fids]
        # Handle names a little differently to avoid an issue with duplicate names
        forced_by_name = [i for i in ALL_OBJS if i.name in _fns]
        forced_by_name.sort(key=lambda i: (score_key(i), i.item_rarity), reverse=True)
        forced_by_name = ordered_keep_by_key(forced_by_name, key=attrgetter("name", "item_slot"), k=1)
        forced_items.extend(forced_by_name)

        if any(item_condition_conflicts_requested_stats(item) for item in forced_items):
            msg = "Forced item has a condition which conflicts with requested stats"
            raise ImpossibleStatError(msg)

        if len(forced_items) < len(_fids) + len(_fns):
            msg = (
                "Unable to force some of these items with your other conditions"
                f"Attempted ids {ns.idforce}, names {ns.nameforce}, found {' '.join(map(str, forced_items))}"
            )
            raise SolveError(msg)

        forced_relics = [i for i in forced_items if i.is_relic]
        if len(forced_relics) > 1:
            msg = "Unable to force multiple relics into one set"
            raise SolveError(msg)

        forced_ring: Iterable[EquipableItem] = ()
        if forced_relics:
            relic = forced_relics[0]
            forced_slots[relic.item_slot] += 1
            try:
                sword_idx = NATION_RELIC_EPIC_IDS.index(relic.item_id)
            except ValueError:
                pass
            else:
                ring_idx = NATION_RELIC_EPIC_IDS[sword_idx + 4]
                fr = next((i for i in ALL_OBJS if i.item_id == ring_idx), None)
                if fr is None:
                    msg = "Couldn't force corresponding nation ring?"
                    raise SolveError(msg)
                forced_ring = (fr,)

        forced_epics = [*(i for i in forced_items if i.is_epic), *(i for i in forced_ring if i not in forced_items)]
        if len(forced_epics) > 1:
            msg = "Unable to force multiple epics into one set"
        if forced_epics:
            epic = forced_epics[0]
            forced_slots[epic.item_slot] += 1

            try:
                ring_idx = NATION_RELIC_EPIC_IDS.index(epic.item_id)
            except ValueError:
                pass
            else:
                sword_idx = NATION_RELIC_EPIC_IDS[ring_idx - 4]
                forced_sword = next((i for i in ALL_OBJS if i.item_id == sword_idx), None)

                if forced_sword is None:
                    msg = "Couldn't force corresponding nation sword?"
                    raise SolveError(msg)

                if forced_sword in forced_relics:
                    pass
                elif forced_relics:
                    msg = "Can't force a nation ring with a non-nation sowrd relic"
                    raise SolveError(msg)
                else:
                    forced_relics.append(forced_sword)
                    forced_slots[forced_sword.item_slot] += 1

        for item in (*forced_epics, *forced_relics):
            try:
                forced_items.remove(item)
            except Exception as exc:
                log.exception("How? (wakforge had this actual error...)", exc_info=exc)

        for item in forced_items:
            forced_slots[item.item_slot] += 1

        for slot, slot_count in forced_slots.items():
            mx = 2 if slot == "LEFT_HAND" else 1
            if slot_count > mx:
                msg = f"Too many forced items in position: {slot}"
                raise SolveError(msg)

        original_forced_counts = forced_slots.copy()

        for item in (*forced_relics, *forced_epics):
            forced_slots[item.item_slot] -= 1

    else:
        forced_items = []
        forced_relics = []
        forced_epics = []

    @lru_cache
    def missing_common_major(item: EquipableItem) -> bool:
        """
        Ignores the cases of: Eternal Sword, Guffet Helm, Lyfamulet
        """
        req = 0
        if item.is_epic or item.is_relic:
            req += 1

        if common_ap_mp_sum_gt_0.get(item.item_slot, 999) <= ns.lv:
            req += 1

        return item.ap + item.mp < req

    _af_items = ordered_keep_by_key([*forced_epics, *forced_relics, *forced_items], attrgetter("item_id"), 1)
    _af_stats: Stats = reduce(add, (i.as_stats() for i in _af_items), Stats())
    _af_slots = [i.item_slot for i in _af_items]
    FINDABLE_AP_MP_NEEDED = sum(attrgetter("ap", "mp")(stat_mins - base_stats - _af_stats))
    findableAP_MP = sum(1 for islot, lv in common_ap_mp_sum_gt_0.items() if islot not in _af_slots and lv <= ns.lv)

    # TODO: dynamic from sql to not need re-checking/expanding each time
    # TODO: Both of these are technically still possible to be impossible if forced slots preclude
    # TODO: some of the below also impossible based on forbidden items...

    eternal_findable = False

    if (not forced_epics) and 7 in allowed_rarities:
        findableAP_MP += 1
    if (not forced_relics) and ns.lv >= 50 and 5 in allowed_rarities:
        findableAP_MP += 1
        if ns.lv >= 200 and "FIRST_WEAPON" not in _af_slots and 26593 not in ns.idforbid:
            findableAP_MP += 1
            eternal_findable = True

    if ns.lv >= 230:
        if "HEAD" not in _af_slots:  # guffet helm
            findableAP_MP += 1
        if "NECK" not in _af_slots:  # lyfamulet
            findableAP_MP += 1

    if point_spread and not point_spread.is_fully_allocated(ns.lv):
        msg = "Literally impossible AP MP reqs (Note: Stats were not fully allocated)"
    else:
        msg = "Literally impossible AP MP reqs"

    if findableAP_MP == FINDABLE_AP_MP_NEEDED and eternal_findable:
        try:
            eternal_sword = next(i for i in ALL_OBJS if i.item_id == 26593)
        except StopIteration:
            raise ImpossibleStatError(msg) from None
        else:
            forced_relics.append(eternal_sword)
            original_forced_counts["FIRST_WEAPON"] += 1

    if findableAP_MP < FINDABLE_AP_MP_NEEDED:
        raise ImpossibleStatError(msg)

    # See interesting_queries.sql, TODO: embed sql data and handle this better

    # ┌───────────────────┬────┬──────────────┬────────────────────────────┐
    # │  Item name (en)   │ ap │   position   │ first ALS bracket ap avail │
    # │ Gobball Amulet    │ 1  │ NECK         │ 20                         │
    # │ Gobball Cape      │ 1  │ BACK         │ 20                         │
    # │ Conquered Raziel  │ 1  │ FIRST_WEAPON │ 50                         │
    # │ Feathered Armor I │ 1  │ CHEST        │ 80                         │
    # │ Niteynite Boots   │ 1  │ LEGS         │ 200                        │
    # │ Disembodier       │ 2  │ FIRST_WEAPON │ 200                        │
    # └───────────────────┴────┴──────────────┴────────────────────────────┘
    # ┌───────────────────────┬────┬───────────────┬────────────────────────────┐
    # │    Item name (en)     │ mp │   position    │ first ALS bracket mp avail │
    # │ Kapow Thongs          │ 1  │ LEGS          │ 50                         │
    # │ Penn Knives           │ 1  │ SECOND_WEAPON │ 50                         │
    # │ Magmacrak Breastplate │ 1  │ CHEST         │ 50                         │
    # │ Chrysalied            │ 1  │ FIRST_WEAPON  │ 50                         │
    # │ Toxy Cloak            │ 1  │ BACK          │ 80                         │
    # │ Celestial Brooch      │ 1  │ NECK          │ 170                        │
    # │ Famished Boots        │ 2  │ LEGS          │ 230                        │
    # │ Gufet'Helm            │ 1  │ HEAD          │ 230                        │
    # │ Age-Old Shovel        │ 2  │ FIRST_WEAPON  │ 230                        │
    # └───────────────────────┴────┴───────────────┴────────────────────────────┘
    # ┌───────────────────────┬────┬───────────────┬────────────────────────────┐
    # │    Item name (en)     │ ra │   position    │ first ALS bracket ra avail │
    # │ Peckish Helmet        │ 1  │ HEAD          │ 35                         │
    # │ Kings' Staff          │ 1  │ FIRST_WEAPON  │ 65                         │
    # │ Polnuds               │ 1  │ LEGS          │ 80                         │
    # │ Aspirant              │ 1  │ NECK          │ 80                         │
    # │ Broken Sword          │ 2  │ FIRST_WEAPON  │ 170                        │
    # │ Beach Bandage         │ 1  │ LEFT_HAND     │ 185                        │
    # │ Moon Aegis            │ 1  │ SECOND_WEAPON │ 185                        │
    # │ Horned Headgear       │ 2  │ HEAD          │ 200                        │
    # │ Hooklettes            │ 1  │ SHOULDERS     │ 200                        │
    # │ YeCh'Ti'Wawa Amulet   │ 2  │ NECK          │ 215                        │
    # │ Destroyer Breastplate │ 1  │ CHEST         │ 230                        │
    # │ Vile IV Emblem        │ 1  │ ACCESSORY     │ 230                        │
    # │ Tinker Belt           │ 1  │ BELT          │ 230                        │
    # └───────────────────────┴────┴───────────────┴────────────────────────────┘
    # ┌─────────────────────────────────┬────┬───────────────┬────────────────────────────┐
    # │         Item name (en)          │ wp │   position    │ first ALS bracket wp avail │
    # │ Beltedy                         │ 1  │ BELT          │ 20                         │
    # │ The Anchor                      │ 1  │ FIRST_WEAPON  │ 50                         │
    # │ Canopy Emblem                   │ 1  │ ACCESSORY     │ 50                         │
    # │ Charming Bow Meow               │ 1  │ PET           │ 50                         │
    # │ Rigid Cire Momore's Rigid Armor │ 1  │ CHEST         │ 65                         │
    # │ Tortuous Escutcheon             │ 1  │ SECOND_WEAPON │ 65                         │
    # │ Synwel's Ring                   │ 1  │ LEFT_HAND     │ 80                         │
    # │ Excarnus Stripes                │ 1  │ SHOULDERS     │ 80                         │
    # │ Balloots                        │ 1  │ LEGS          │ 200                        │
    # │ Sumorse Cape                    │ 1  │ BACK          │ 215                        │
    # │ Amulet of Time                  │ 1  │ NECK          │ 230                        │
    # └─────────────────────────────────┴────┴───────────────┴────────────────────────────┘

    # fmt: off
    # TODO: also handle wp, ra
    f_avail = {
        "ap": {"NECK": (20,), "BACK": (20, ), "FIRST_WEAPON": (50, 200), "CHEST": (80,), "LEGS": (200,)},
        "mp": {
            # We leave out the +2 mp weapon because it conflicts with a lower level dagger
            "LEGS": (50, 230), "SECOND_WEAPON": (50,), "CHEST": (50,), "FIRST_WEAPON": (50,),
            "BACK": (80,), "NECK": (170,), "HEAD": (230,)
        },
        "ra": {
            "HEAD": (35, 200), "FIRST_WEAPON": (65, 170), "LEGS": (80,), "NECK": (80, 215),
            "LEFT_HAND": (185,), "SHOULDERS": (200,), "CHEST": (230,), "ACCESSORY": (230,),
            "BELT": (230,),
        },
    }
    # fmt: on

    for stat, data_dict in f_avail.items():
        needed: int = attrgetter(stat)(stat_mins - base_stats - _af_stats)

        if (not forced_epics) and 7 in allowed_rarities:
            if stat in ("mp", "ap"):
                needed -= 1
            if stat == "ra":
                if ns.lv >= 140 >= LOW_BOUND:
                    needed -= 1  # sigiknight ring
                elif ns.lv >= 155 >= LOW_BOUND:
                    needed -= 1  # golden belt
                elif ns.lv < 200 and ns.lv >= 185 >= LOW_BOUND:
                    needed -= 1  # azure dreggon headgear
            if stat == "ap":  # noqa: SIM102
                # Harlock's boots
                if ns.lv >= 140 >= LOW_BOUND:
                    needed -= 1

        if (not forced_relics) and 5 in allowed_rarities:
            if ns.lv >= 50 and stat in ("mp", "ap"):
                needed -= 1
            if stat == "ra":
                if ns.lv >= 140 >= LOW_BOUND:
                    # asse shield or soft oak hat
                    needed -= 1
                elif ns.lv >= 155 >= LOW_BOUND:
                    # golden keychain
                    needed -= 1
                elif ns.lv < 200 and ns.lv >= 180 >= LOW_BOUND:
                    # Moon epaulettes
                    needed -= 1

        for slot, lvs in data_dict.items():
            if _af_slots.count(slot) >= (2 if slot == "LEFT_HAND" else 1):
                continue
            if slot == "SECOND_WEAPON" and any(i.disables_second_weapon for i in _af_items):
                continue

            s = sum(1 for lv in lvs if lv <= ns.lv)

            needed -= s

        if needed > 0:
            msg = f"Impossible to get {getattr(stat_mins, stat, '??')} {stat} with the specified conditions"
            if point_spread and not point_spread.is_fully_allocated(ns.lv):
                msg += " (Note: Stats were not fully allocated)"
            raise ImpossibleStatError(msg)

    def initial_filter(item: EquipableItem) -> bool:
        return bool(
            (item.item_id not in FORBIDDEN)
            and (item.name not in FORBIDDEN_NAMES)
            and (not has_currently_unhandled_item_condition(item))
            and ((item.item_rarity in allowed_rarities) or (item.item_slot in ("MOUNT", "PET")))
            and (findableAP_MP > FINDABLE_AP_MP_NEEDED or not missing_common_major(item))
            and not item_condition_conflicts_requested_stats(item)
        )

    OBJS: Final[list[EquipableItem]] = list(filter(initial_filter, ALL_OBJS))
    del ALL_OBJS

    AOBJS: collections.defaultdict[str, list[EquipableItem]] = collections.defaultdict(list)

    log.info("Culling items that aren't up to scratch.")

    for item in filter(level_filter, filter(minus_relicepic, OBJS)):
        AOBJS[item.item_slot].append(item)

    for stu in AOBJS.values():
        stu.sort(key=score_key, reverse=True)

    def compat_with_forced(item: EquipableItem) -> bool:
        c = (original_forced_counts or {}).get(item.item_slot, 0)
        if c >= (2 if item.item_slot == "LEFT_HAND" else 1):
            return False
        if item.item_slot == "SECOND_WEAPON":  # noqa: SIM102
            if any(i.disables_second_weapon for i in (*forced_items, *forced_epics, *forced_relics)):
                return False
        return True

    relics = forced_relics or [
        item
        for item in OBJS
        if item.is_relic
        and initial_filter(item)
        and compat_with_forced(item)
        and relic_epic_level_filter(item)
        and (findableAP_MP > FINDABLE_AP_MP_NEEDED or not missing_common_major(item))
        and item.item_id not in NATION_RELIC_EPIC_IDS
    ]
    epics = forced_epics or [
        item
        for item in OBJS
        if item.is_epic
        and initial_filter(item)
        and compat_with_forced(item)
        and relic_epic_level_filter(item)
        and (findableAP_MP > FINDABLE_AP_MP_NEEDED or not missing_common_major(item))
        and item.item_id not in NATION_RELIC_EPIC_IDS
    ]

    _soft_unobtainable = load_item_source_data().legacy_items - {
        item.item_id for item in (*forced_items, *forced_relics, *forced_epics)
    }

    solve_CANIDATES: dict[str, list[EquipableItem]] = {
        k: [item for item in v if item.item_id not in _soft_unobtainable] for k, v in AOBJS.items()
    }


    sim_keys = {"disables_second_weapon", *ALWAYS_SIMMED}
    if passives and 5100 in passives:
        sim_keys.add("block")
    if ns.unraveling or ns.wakfu_class is ClassesEnum.Eca:
        sim_keys.add("critical_hit")
    if ns.unraveling:
        sim_keys.add("critical_mastery")

    @lru_cache(128)
    def needs_full_sim_key(item: EquipableItem, _getter = attrgetter(*sim_keys)) -> Hashable:  # pyright: ignore[reportMissingParameterType]
        return _getter(item)

    if original_forced_counts:
        for slot, count in original_forced_counts.items():
            if (slot != "LEFT_HAND" and count == 1) or (slot == "LEFT_HAND" and count == 2):
                solve_CANIDATES.pop(slot, None)
            elif slot == "LEFT_HAND" and count == 1:
                names = {i.name for i in forced_items if i.name}
                for canidate in solve_CANIDATES[slot][::-1]:
                    if canidate.name in names:
                        solve_CANIDATES[slot].remove(canidate)

    solve_ONEH = (
        [i for i in solve_CANIDATES["FIRST_WEAPON"] if not i.disables_second_weapon] if "FIRST_WEAPON" in solve_CANIDATES else []
    )
    solve_TWOH = (
        [i for i in solve_CANIDATES["FIRST_WEAPON"] if i.disables_second_weapon] if "FIRST_WEAPON" in solve_CANIDATES else []
    )
    solve_DAGGERS = (
        [i for i in solve_CANIDATES["SECOND_WEAPON"] if i.item_type == 112] if "SECOND_WEAPON" in solve_CANIDATES else []
    )
    if ns.skipshields or "SECOND_WEAPON" not in solve_CANIDATES:
        solve_SHIELDS = []
    else:
        solve_SHIELDS = [i for i in solve_CANIDATES["SECOND_WEAPON"] if i.item_type == 189]

    for key in ("FIRST_WEAPON", "SECOND_WEAPON"):
        solve_CANIDATES.pop(key, None)

    # TODO: Break this loop out into dedicated function for pruning item pool
    for items in (solve_ONEH, solve_TWOH, solve_DAGGERS, *solve_CANIDATES.values()):
        if not items:
            continue
        slot = items[0].item_slot

        rarity_handler = attrgetter("item_rarity", "name", "is_souvenir", "is_relic", "is_epic")
        items.sort(key=rarity_handler, reverse=True)
        uniq_handler = attrgetter("name", "is_souvenir", "is_relic", "is_epic")
        inplace_ordered_keep_by_key(items, uniq_handler)
        items.sort(key=crit_score_key, reverse=True)

        k = 2 if slot == "LEFT_HAND" else 1

        if not ns.exhaustive:
            bck = items.copy()
            best = items[: ns.search_depth + k]
            items.clear()
            items.extend(best)
            inplace_ordered_keep_by_key(bck, needs_full_sim_key, k)

            for val in (0, 1, 2):
                while True:
                    # avoid excluding too many items with some pathological -stat items
                    # see Nonsensical epps (item id: 29278)
                    added = False
                    for stat in ("ap", "mp", "ra", "wp"):
                        x = attrgetter(stat)
                        c_added = 0
                        for item in ordered_keep_by_key([i for i in bck if i not in items], x, k):
                            if x(item) >= val:
                                items.append(item)
                                added = True
                                c_added += 1
                                if c_added >= k:
                                    break

                    if not added:
                        break

                    _tc_items = [i for i in items if get_item_conditions(i) == (SetMinimums(), SetMaximums())]

                    if len([i for i in _tc_items if all(s >= val for s in attrgetter("ap", "mp", "ra", "wp")(i))]) >= k:
                        break

        items.sort(key=crit_score_key, reverse=True)
        inplace_ordered_keep_by_key(items, needs_full_sim_key, k)

    relics.sort(key=lambda r: (score_key(r), r.item_slot), reverse=True)
    inplace_ordered_keep_by_key(relics, needs_full_sim_key)
    epics.sort(key=lambda e: (score_key(e), e.item_slot), reverse=True)
    inplace_ordered_keep_by_key(epics, needs_full_sim_key)

    if ns.lwx:
        solve_DAGGERS.append(EquipableItem(-2, ns.lv, 4, 112, elemental_mastery=int(ns.lv * 1.5)))
    if sublimations:
        c = 0
        for sub in sublimations:
            if sub == 28908:
                c += 1
            elif sub == 28807:
                c += 2
            elif sub == 28909:
                c += 3
        x = 0.25 * min(c, 6)
        if x > 0:
            solve_DAGGERS.append(EquipableItem(-2, ns.lv, 4, 112, elemental_mastery=int(ns.lv * x)))

    # Tt be reused below

    for item in (*forced_relics, *forced_epics):
        if item.item_type == 112:
            solve_DAGGERS = [item]
        elif item.item_id == 189:
            solve_SHIELDS = [item]

        if item.item_slot == "FIRST_WEAPON":
            if item.disables_second_weapon:
                solve_TWOH = [item]
            else:
                solve_ONEH = [item]

    if ns.skipshields:
        canidate_weapons = (*itertools.product(solve_ONEH, (solve_DAGGERS + solve_SHIELDS)),)
    else:
        canidate_weapons = (
            *((two_hander,) for two_hander in solve_TWOH),
            *itertools.product(solve_ONEH, (solve_DAGGERS + solve_SHIELDS)),
        )

    weapon_key_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], Hashable]

    weapon_key_func = lambda w: (
        isinstance(w, tuple),
        *(sum(a) for a in zip(*(needs_full_sim_key(i) for i in w))),
    )

    @lru_cache(128)
    def weapon_score_func(w: Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]) -> float:
        return sum(map(score_key, w))

    srt_w = sorted(canidate_weapons, key=weapon_score_func, reverse=True)
    canidate_weapons = ordered_keep_by_key(srt_w, weapon_key_func)

    solve_BEST_LIST: list[tuple[float, list[EquipableItem]]] = []

    log.info("Considering the options...")

    extra_pairs: list[tuple[EquipableItem, EquipableItem]] = []

    if not (forced_relics or forced_epics) and (LOW_BOUND <= 200 <= ns.lv):
        for i in range(4):
            sword_id, ring_id = NATION_RELIC_EPIC_IDS[i], NATION_RELIC_EPIC_IDS[i + 4]
            sword = next((i for i in OBJS if i.item_id == sword_id), None)
            ring = next((i for i in OBJS if i.item_id == ring_id), None)
            if sword and ring:
                extra_pairs.append((sword, ring))

    log.info("Considering some items... This may take a few moments")

    epics.sort(key=score_key, reverse=True)
    relics.sort(key=score_key, reverse=True)
    kf: Callable[[EquipableItem], Hashable] = lambda i: (i.item_slot, needs_full_sim_key(i))
    inplace_ordered_keep_by_key(epics, kf)
    inplace_ordered_keep_by_key(relics, kf)

    def re_key_func(
        pair: tuple[EquipableItem | None, EquipableItem | None],
        _as_attrgetter=AS_ATTR_GETTER, # pyright: ignore[reportMissingParameterType]
    ) -> Hashable:
        if not any(pair):
            return 0
        disables_second = any(i.disables_second_weapon for i in pair if i)
        positions = [i.item_slot for i in pair if i]
        pos_key = "-".join(sorted(positions))
        re_s = [i.as_stats() for i in pair if i]
        sc = re_s[0]
        if len(re_s) > 1:
            sc = sc + re_s[1]
        ks = _as_attrgetter(sc)
        return (pos_key, disables_second, *ks)

    distribs = {
        k: statistics.NormalDist.from_samples(crit_score_key(i) for i in v) if len(v) > 1 else None
        for k, v in solve_CANIDATES.items()
    }

    ONEH_distrib = statistics.NormalDist.from_samples(crit_score_key(i) for i in solve_ONEH) if len(solve_ONEH) > 1 else None
    TWOH_distrib = statistics.NormalDist.from_samples(crit_score_key(i) for i in solve_TWOH) if len(solve_TWOH) > 1 else None
    OFF_HANDS = solve_DAGGERS + solve_SHIELDS
    OFF_HAND_distrib = statistics.NormalDist.from_samples(crit_score_key(i) for i in OFF_HANDS) if len(OFF_HANDS) > 1 else None

    @lru_cache
    def re_score_key(pair: tuple[EquipableItem | None, EquipableItem | None]) -> tuple[int, float, float]:
        v, s = 0, 0
        unknown = 0
        for re in pair:
            if re:
                s += crit_score_key(re)
                if re.item_slot == "FIRST_WEAPON":
                    dist = TWOH_distrib if re.disables_second_weapon else ONEH_distrib
                elif re.item_slot == "SECOND_WEAPON":
                    dist = OFF_HAND_distrib
                else:
                    dist = distribs.get(re.item_slot, None)

                if dist:
                    try:
                        v += dist.zscore(crit_score_key(re))
                    except statistics.StatisticsError:
                        unknown = -1
                else:
                    unknown = -1
        return unknown, v, s

    pairs: list[tuple[EquipableItem | None, EquipableItem | None]]

    def valid(item_pair: tuple[EquipableItem | None, EquipableItem | None]) -> bool:
        relic, epic = item_pair
        if relic and epic and relic.item_slot == epic.item_slot:
            if relic.item_slot != "LEFT_HAND":
                return False
            k = 0
            if relic not in forced_relics:
                k += 1
            if epic not in forced_epics:
                k += 1

            if 2 - forced_slots["LEFT_HAND"] < k:
                return False
        else:
            for item in item_pair:
                if item and item not in (*forced_relics, *forced_epics):
                    slot_max = 1 if item.item_slot == "LEFT_HAND" else 0
                    if forced_slots[item.item_slot] > slot_max:
                        return False
        return True

    pairs = [pair for pair in (*itertools.product(relics or [None], epics or [None]), *extra_pairs) if valid(pair)]

    pairs.sort(key=re_score_key, reverse=True)
    canidate_re_pairs = ordered_keep_by_key(pairs, re_key_func)
    pairs.sort(key=lambda p: re_score_key(p)[1:], reverse=True)

    if ns and not ns.exhaustive:
        canidate_re_pairs = canidate_re_pairs[: ns.hard_cap_depth]
        for slot, items in solve_CANIDATES.items():
            bck = items.copy()
            k = 1
            if slot == "LEFT_HAND":
                k = 2
            elif slot == "PET":
                k = 4
            elif slot == "CHEST":
                k = 5
            items.clear()
            items.extend(bck[: k + ns.search_depth])

            # This can happen if people don't give the solver good infomration
            # like omitting elements at low levels, while also not requesting
            # a combination ap+mp that is max available
            # Frankly, I don't want to support this kind of build. The solver is intended to
            # give people things that are going to help them, and builds like this won't,
            # but whatever. Doing this for now.
            if all(missing_common_major(item) for item in items):
                it = next(iter(i for i in bck if not missing_common_major(i)), None)
                if it is not None:
                    items.append(it)
            # wp items really suck
            needed_wp = stat_mins.wp - base_stats.wp - _af_stats.wp
            for it in items:
                if it.wp > 0:
                    needed_wp -= 1
            for _ in range(min(k, needed_wp)):
                for item in bck:
                    if item.wp > 0 and item not in items:
                        items.append(item)
                        break
            # so do range, but less so
            needed_ra = stat_mins.ra - base_stats.ra - _af_stats.ra
            if needed_ra > 0:
                for stat in ("ap", "mp"):
                    getter = attrgetter("ra", stat)
                    c = 0
                    for item in items:
                        ra, other = getter(item)
                        if ra > 0 and other > 0:
                            c += ra
                            if c >= k:
                                break
                    else:
                        found = False
                        for val in reversed(range(1, needed_ra + 1)):
                            if found:
                                break
                            for item in bck:
                                if item not in items:
                                    ra, other = getter(item)
                                    if ra >= val and other > 0:
                                        items.append(item)
                                        found = True
                                        break

        canidate_weapons = canidate_weapons[: int(ns.hard_cap_depth)]

    if ns.dry_run:
        ret: list[EquipableItem] = []
        ret.extend(filter(None, itertools.chain.from_iterable(canidate_re_pairs)))
        ret.extend(forced_items)
        for k, v in solve_CANIDATES.items():
            if "WEAPON" not in k:
                ret.extend(v)

        for weps in canidate_weapons:
            ret.extend(weps)
        return [(0, ordered_keep_by_key(ret, attrgetter("item_id")))]

    # everything below this line is performance sensitive, and runtime is based on how much the above
    # managed to reduce the permuations of possible gear.

    solve_CANIDATES.pop("WEAPONS", None)


    # Everything in this section can be improved.
    # Major things to consider:
    #   - do an initial pass with random sampling, using the results to further prune options
    #        - downside: nondeterministic output
    #        - upside: initial prior attempt resulted in speed increases of about 2x
    #        verdict: revisit this after other speed improvements are explored if speed is still an issue
    #   - Start with solving best non-relic epics and discard any relic/epics that can't beat that immediately.
    #   - Restructure data to allow this to be a vectorizable problem
    #      - Challenges exist here around class specific behavior

    filtered_re_pairs: list[tuple[EquipableItem | None, EquipableItem | None]] = []

    for (relic, epic) in canidate_re_pairs:

        if relic and epic:
            if relic.item_slot == epic.item_slot != "LEFT_HAND":
                continue

            if relic.disables_second_weapon and epic.item_slot == "SECOND_WEAPON":
                continue

            if epic.disables_second_weapon and relic.item_slot == "SECOND_WEAPON":
                continue

        filtered_re_pairs.append((relic, epic))

    re_len = len(filtered_re_pairs)

    if "pyodide" in sys.modules:
        for idx, (relic, epic) in enumerate(filtered_re_pairs, 1):

            if progress_callback:
                progress_callback(idx, re_len)

            solve_BEST_LIST.extend(
                inner_solve(relic, epic, solve_CANIDATES, forced_slots, forced_items, solve_DAGGERS, solve_SHIELDS, solve_ONEH, canidate_weapons, ns, base_stats, stat_mins, stat_maxs, passives, sublimations)
            )

    else:

        import multiprocessing as mp
        pool = mp.Pool()
        args = [(relic, epic, solve_CANIDATES, forced_slots, forced_items, solve_DAGGERS, solve_SHIELDS, solve_ONEH, canidate_weapons, ns, base_stats, stat_mins, stat_maxs, passives, sublimations) for relic, epic in filtered_re_pairs]

        results = pool.starmap(inner_solve, args)

        for res in results:
            solve_BEST_LIST.extend(res)

    solve_BEST_LIST.sort(reverse=True)
    solve_BEST_LIST.sort(key=itemgetter(0), reverse=True)
    solve_BEST_LIST = solve_BEST_LIST[:5]

    return solve_BEST_LIST


from typing import Mapping, Sequence

def inner_solve(
    relic: EquipableItem | None,
    epic: EquipableItem | None,
    solve_CANIDATES: Mapping[str, list[EquipableItem]],
    forced_slots: Mapping[str, int],
    forced_items: Sequence[EquipableItem],
    solve_DAGGERS: Sequence[EquipableItem],
    solve_SHIELDS: Sequence[EquipableItem],
    solve_ONEH: Sequence[EquipableItem],
    canidate_weapons: Sequence[tuple[EquipableItem] | tuple[EquipableItem, EquipableItem]],
    ns: v1Config,
    base_stats: Stats,
    stat_mins: SetMinimums,
    stat_maxs: SetMaximums,
    passives: Sequence[int] | None,
    sublimations: Sequence[int] | None,
) -> list[tuple[float, list[EquipableItem]]]:



    def _score_key(item: EquipableItem | Stats | None) -> float:
        score = 0.0
        if not item:
            return score

        elemental_modifier = 1.2 if ns.wakfu_class == ClassesEnum.Huppermage else 1

        score += item.elemental_mastery * elemental_modifier
        if ns.melee:
            score += item.melee_mastery
        if ns.dist:
            score += item.distance_mastery
        if ns.zerk and ns.negzerk not in ("half", "full"):
            score += item.berserk_mastery
        else:
            if item.berserk_mastery < 0:
                if ns.negzerk == "full":
                    mul = 1.0
                elif ns.negzerk == "half":
                    mul = 0.5
                else:
                    mul = 0.0

                score += item.berserk_mastery * mul

        if ns.rear and ns.negrear not in ("full", "half"):
            score += item.rear_mastery
        else:
            if item.rear_mastery < 0:
                if ns.negrear == "full":
                    mul = 1.0
                elif ns.negrear == "half":
                    mul = 0.5
                else:
                    mul = 0.0

                score += item.rear_mastery * mul

        if ns.heal:
            score += item.healing_mastery

        if ns.num_mastery == 1:
            score += item.mastery_1_element * elemental_modifier
        if ns.num_mastery <= 2:
            score += item.mastery_2_elements * elemental_modifier
        if ns.num_mastery <= 3:
            score += item.mastery_3_elements * elemental_modifier

        # This isn't perfect, Doziak epps are weird.
        if (n := ns.elements.bit_count()) and not isinstance(item, Stats):
            element_vals = 0
            if ElementsEnum.air in ns.elements:
                element_vals += item.air_mastery
            if ElementsEnum.earth in ns.elements:
                element_vals += item.earth_mastery
            if ElementsEnum.water in ns.elements:
                element_vals += item.water_mastery
            if ElementsEnum.fire in ns.elements:
                element_vals += item.fire_mastery
            score += element_vals / n * elemental_modifier

        return score

    score_key = lru_cache(512)(_score_key)

    solve_BEST_LIST: list[tuple[float, list[EquipableItem]]] = []

    score_key = lru_cache()(_score_key)

    @lru_cache(128)
    def weapon_score_func(w: Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]) -> float:
        return sum(map(score_key, w))

    l_add = lru_cache(1024)(add)
    l_and = lru_cache(and_)

    REM_SLOTS = [
        "LEGS",
        "BACK",
        "HEAD",
        "CHEST",
        "SHOULDERS",
        "BELT",
        "LEFT_HAND",
        "LEFT_HAND",
        "NECK",
        "ACCESSORY",
        "MOUNT",
        "PET",
    ]

    # This is a slot we allow building without, sets without will be worse ofc...
    if "ACCESSORY" not in solve_CANIDATES:  # noqa: SIM102
        if not ((relic and relic.item_slot == "ACCESSORY") or (epic and epic.item_slot == "ACCESSORY")):
            try:
                REM_SLOTS.remove("ACCESSORY")
            except ValueError:
                pass

    for slot, count in forced_slots.items():
        for _ in range(count):
            try:
                REM_SLOTS.remove(slot)
            except ValueError:
                pass

    if relic and relic.item_slot not in REM_SLOTS and "WEAPON" not in relic.item_slot:
        return [(0, [])]
    if epic and epic.item_slot not in REM_SLOTS and "WEAPON" not in epic.item_slot:
        return [(0, [])]

    main_hand_disabled = False
    off_hand_disabled = False

    for item in (*forced_items, relic, epic):
        if item is None:
            continue
        if item.item_slot == "FIRST_WEAPON":
            main_hand_disabled = True
            if item.disables_second_weapon:
                off_hand_disabled = True
        elif item.item_slot == "SECOND_WEAPON":
            off_hand_disabled = True
        elif item.is_epic or item.is_relic:
            try:
                REM_SLOTS.remove(item.item_slot)
            except ValueError:
                continue

    weapons: list[tuple[EquipableItem] | tuple[EquipableItem, EquipableItem]] = []
    if not (main_hand_disabled and off_hand_disabled):
        REM_SLOTS.append("WEAPONS")

        if main_hand_disabled:
            s = [*solve_DAGGERS, *solve_SHIELDS]
            s.sort(key=score_key, reverse=True)
            weapons = [(i,) for i in ordered_keep_by_key(s, lambda i: (i.ap, i.mp, i.ra, i.wp))]
        elif off_hand_disabled:
            weapons = [(i,) for i in ordered_keep_by_key(solve_ONEH, lambda i: (i.ap, i.mp, i.ra, i.wp))]
        else:
            weapons = list(canidate_weapons)

        weapons.sort(key=weapon_score_func, reverse=True)

    try:
        k = REM_SLOTS.count("LEFT_HAND")
        ring_pairs = list(itertools.combinations(solve_CANIDATES["LEFT_HAND"], k)) if k > 0 else ()
        cans = [ring_pairs, *(solve_CANIDATES[k] for k in REM_SLOTS if k not in ("LEFT_HAND", "WEAPONS"))]
        if "WEAPONS" in REM_SLOTS:
            cans.append(weapons)
    except KeyError as exc:
        log.debug("Constraints may have removed too many items slot: %s", exc.args[0])
        return [(0, [])]

    filtered = filter(None, cans)

    re_st = base_stats
    if relic:
        re_st += relic.as_stats()
    if epic:
        re_st += epic.as_stats()

    for raw_items in itertools.product(*filtered):

        items = list(forced_items)
        statline: Stats = re_st
        for ri in raw_items:
            if type(ri) is EquipableItem:
                items.append(ri)
            else:
                items.extend(ri)

        statline: Stats = reduce(l_add, [i.as_stats() for i in items], re_st)
        if ns.twoh and any(i.disables_second_weapon for i in items):
            statline = apply_w2h(statline)

        # GLOBAL GAME CONDITION
        if statline.critical_hit < -10:
            continue

        mns = stat_mins
        mxs = stat_maxs

        for gmi, gmx in map(get_item_conditions, filter(None, (*items, relic, epic))):
            if gmi:
                mns = l_and(mns, gmi)
            if gmx:
                mxs = l_and(mxs, gmx)


        if not mns <= statline <= mxs:
            continue

        critical_hit = statline.critical_hit + 3

        # Note: keep the class here even if it isn't needed for ease of reference

        # innate passive
        if ns.wakfu_class == ClassesEnum.Ecaflip and critical_hit > 100:
            statline += Stats(fd=0.5 * (critical_hit - 100))

        # Bravery
        if ns.wakfu_class == ClassesEnum.Iop and passives and 5100 in passives and ns.lv >= 90:
            block_mod = min(max(0, statline.block // 2), 20)
            if block_mod:
                statline += Stats(critical_hit=block_mod)

        # Sram to the bone
        if ns.wakfu_class == ClassesEnum.Sram and passives and 4610 in passives and ns.lv >= 100:
            # TODO: (?) We assume shards will make up any missing lock/dodge right now
            statline += Stats(critical_hit=20 if ns.lv < 200 else 30)

        if ns.wakfu_class == ClassesEnum.Masq and passives:
            # TODO: (?) We assume shards will make up any missing lock/dodge right now
            if 7096 in passives and ns.lv >= 20:  # artful locker
                melee_mod = min(max(0, ns.lv * 2), ns.lv * 2)
                statline += Stats(melee_mastery=melee_mod)
            if 7109 in passives and ns.lv >= 85:  # artful dodge
                distance_mod = min(max(0, ns.lv * 2), ns.lv * 2)
                statline += Stats(distance_mastery=distance_mod)

        UNRAVEL_ACTIVE = ns.unraveling and critical_hit >= 40

        crit_chance = max(min(critical_hit, 100), 0)  # engine crit rate vs stat

        _is = base_stats
        for item in (*items, relic, epic):
            if item is not None:
                _is += item.as_stats()

        fd_mod = 0
        if _is.get_secondary_sum() <= 0:
            if sublimations and 29874 in sublimations:
                # inflexibility 2
                _is += Stats(
                    elemental_mastery=int(_is.elemental_mastery * 0.15),
                    mastery_1_element=int(_is.mastery_1_element * 0.15),
                    mastery_2_elements=int(_is.mastery_2_elements * 0.15),
                    mastery_3_elements=int(_is.mastery_2_elements * 0.15),
                )
            if sublimations:
                neutrality_c = 0
                for sub in sublimations:
                    if sub == 29001:
                        neutrality_c += 1
                    elif sub == 29002:
                        neutrality_c += 2
                    elif sub == 29003:
                        neutrality_c += 3

                fd_mod = 8 * min(neutrality_c, 4)

        base_score = score_key(_is)

        if UNRAVEL_ACTIVE:
            base_score += statline.critical_mastery * (1.2 if ns.wakfu_class == ClassesEnum.Huppermage else 1)
            non_crit_score = base_score * (100 - crit_chance) / 100
            crit_score = base_score * (crit_chance) / 100
            crit_score *= 1.25
        else:
            non_crit_score = base_score * (100 - crit_chance) / 100
            non_crit_score *= (100 + statline.fd) / 100 + fd_mod

            crit_score = base_score + statline.critical_mastery
            crit_score *= (crit_chance) / 100
            crit_score *= (100 + statline.fd) / 100 + fd_mod
            crit_score *= 1.25

        score = crit_score + non_crit_score

        worst_kept = min(i[0] for i in solve_BEST_LIST) if 0 < len(solve_BEST_LIST) < 3 else 0

        if score > worst_kept:
            filtered = [i for i in (*items, relic, epic) if i]
            filtered.sort(key=lambda i: i.item_id)

            tup = (score, filtered)
            solve_BEST_LIST.sort(key=itemgetter(0), reverse=True)
            solve_BEST_LIST = solve_BEST_LIST[:5]
            solve_BEST_LIST.append(tup)
            solve_BEST_LIST.sort(key=itemgetter(0), reverse=True)

    return solve_BEST_LIST
