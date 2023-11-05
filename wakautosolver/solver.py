"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import argparse

# pyright: reportPrivateUsage=false
# pyright: reportConstantRedefinition=false
import collections
import itertools
import logging
import sys
from collections.abc import Callable, Hashable, Iterable, Iterator
from functools import lru_cache, reduce
from operator import add, and_, attrgetter, itemgetter, mul
from typing import Final, Protocol, TypeVar

import tqdm

from .object_parsing import EquipableItem, _locale
from .restructured_types import SetMaximums, SetMinimums, Stats, generate_filter, v1Config
from .unobs import get_unobtainable_ids
from .utils import only_once

T = TypeVar("T")

log = logging.getLogger("solver")


T_contra = TypeVar("T_contra", contravariant=True)


class SupportsWrite(Protocol[T_contra]):
    def write(self, s: T_contra, /) -> object:
        ...


@only_once
def setup_logging(output: SupportsWrite[str]) -> None:
    handler = logging.StreamHandler(output)
    formatter = logging.Formatter("%(message)s", datefmt="%Y-%m-%d %H:%M:%S", style="%")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def ordered_unique_by_key(it: Iterable[T], key: Callable[[T], Hashable]) -> list[T]:
    seen_set: set[Hashable] = set()
    return [i for i in it if not ((k := key(i)) in seen_set or seen_set.add(k))]


class SolveError(Exception):
    pass


def solve(ns: v1Config, ignore_missing_items: bool = False) -> list[tuple[float, list[EquipableItem]]]:
    """Still has some debug stuff in here, will be refactoring this all later."""

    _locale.set(ns.locale)

    # ## Everything in this needs abstracting into something
    # that can handle user input and be more dynamic.
    # ## Could benefit from some optimizations here and there.

    ALL_OBJS = EquipableItem.from_bz2_bundled()

    allowed_rarities = ns.allowed_rarities or list(range(1, 8))
    if ns.forbid_rarity:
        allowed_rarities = [i for i in allowed_rarities if i not in ns.forbid_rarity]

    LV_TOLERANCE = ns.tolerance
    ITEM_SEARCH_DEPTH = ns.search_depth

    AP = ns.ap
    MP = ns.mp
    RA = ns.ra
    WP = ns.wp
    HIGH_BOUND = ns.lv
    LOW_BOUND = HIGH_BOUND - LV_TOLERANCE
    UNRAVELING = ns.unraveling
    SKIP_SHIELDS = ns.skipshields
    LIGHT_WEAPON_EXPERT = ns.lwx
    WEILD_TYPE_TWO_HANDED = ns.twoh
    BASE_CRIT_CHANCE = 3 + ns.bcrit
    BASE_CRIT_MASTERY = ns.bcmast
    BASE_RELEV_MASTERY = ns.bmast
    SKIP_TWO_HANDED = ns.skiptwo_hand

    if WEILD_TYPE_TWO_HANDED:
        AP -= 2
        MP += 2

    @lru_cache
    def sort_key(item: EquipableItem | None) -> float:
        if not item:
            return 0

        score = item._elemental_mastery
        if ns.melee:
            score += item._melee_mastery
        if ns.dist:
            score += item._distance_mastery
        if ns.zerk:
            score += item._berserk_mastery
        else:
            if item._berserk_mastery < 0:
                if ns.negzerk == "full":
                    mul = 1
                elif ns.negzerk == "half":
                    mul = 0.5
                else:
                    mul = 0

                score += item._berserk_mastery * mul

        if ns.rear:
            score += item._rear_mastery
        else:
            if item._rear_mastery < 0:
                if ns.negrear == "full":
                    mul = 1
                elif ns.negrear == "half":
                    mul = 0.5
                else:
                    mul = 0

                score += item._rear_mastery * mul

        if ns.heal:
            score += item._healing_mastery

        if ns.num_mastery == 1:
            score += item._mastery_1_element
        if ns.num_mastery <= 2:
            score += item._mastery_2_elements
        if ns.num_mastery <= 3:
            score += item._mastery_3_elements

        return score

    def has_currently_unhandled_item_condition(item: EquipableItem) -> bool:
        return any(condition.unhandled() for condition in item.conditions)

    def sort_key_initial(item: EquipableItem) -> float:
        return (
            sort_key(item)
            + 100 * (max(item._mp + item._ap, 0))
            + 50 * (max(item._wp + item._range, 0))
            + item._critical_mastery * (min(BASE_CRIT_MASTERY + 20, 100)) / 100
        )

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

    FORBIDDEN = list(get_unobtainable_ids())

    if ns and ns.idforbid:
        FORBIDDEN.extend(ns.idforbid)

    # locale based, only works if user is naming it in locale used and case sensitive currently.
    FORBIDDEN_NAMES: list[str] = ns.forbid if (ns and ns.forbid) else []

    def initial_filter(item: EquipableItem) -> bool:
        return bool(
            (item._item_id not in FORBIDDEN)
            and (item.name not in FORBIDDEN_NAMES)
            and (not has_currently_unhandled_item_condition(item))
            and (item._item_rarity in allowed_rarities)
        )

    def level_filter(item: EquipableItem) -> bool:
        return HIGH_BOUND >= item._item_lv >= max(LOW_BOUND, 1)

    def relic_epic_level_filter(item: EquipableItem) -> bool:
        """The unreasonable effectiveness of these two rings extends them a bit"""
        if item._item_id == 9723:  # gelano
            return 140 >= HIGH_BOUND >= 65
        if item._item_id == 27281:  # bagus shushu
            return 185 >= HIGH_BOUND >= 125
        return HIGH_BOUND >= item._item_lv >= LOW_BOUND

    def minus_relicepic(item: EquipableItem) -> bool:
        return not (item.is_epic or item.is_relic)

    OBJS: Final[list[EquipableItem]] = list(filter(initial_filter, ALL_OBJS))
    del ALL_OBJS

    forced_slots: collections.Counter[str] = collections.Counter()
    if ns and (ns.idforce or ns.nameforce):
        _fids = ns.idforce or ()
        _fns = ns.nameforce or ()

        forced_items = [i for i in OBJS if i._item_id in _fids]
        # Handle names a little differently to avoid an issue with duplicate names
        forced_by_name = [i for i in OBJS if i.name in _fns]
        forced_by_name.sort(key=sort_key_initial, reverse=True)
        forced_by_name = ordered_unique_by_key(forced_by_name, key=attrgetter("name", "item_slot"))
        forced_items.extend(forced_by_name)

        if len(forced_items) < len(_fids) + len(_fns) and not ignore_missing_items:
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
                sword_idx = NATION_RELIC_EPIC_IDS.index(relic._item_id)
            except ValueError:
                pass
            else:
                ring_idx = NATION_RELIC_EPIC_IDS[sword_idx + 4]
                fr = next((i for i in OBJS if i._item_id == ring_idx), None)
                if fr is None:
                    msg = "Couldn't force corresponding nation ring?"
                    raise SolveError(msg)
                forced_ring = (fr,)

        forced_epics = [*(i for i in forced_items if i.is_epic), *forced_ring]
        if len(forced_epics) > 1:
            msg = "Unable to force multiple epics into one set"
        if forced_epics:
            epic = forced_epics[0]
            forced_slots[epic.item_slot] += 1

            try:
                ring_idx = NATION_RELIC_EPIC_IDS.index(epic._item_id)
            except ValueError:
                pass
            else:
                sword_idx = NATION_RELIC_EPIC_IDS[ring_idx - 4]
                forced_sword = next((i for i in OBJS if i._item_id == sword_idx), None)

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
            forced_items.remove(item)

        for item in forced_items:
            forced_slots[item.item_slot] += 1

        for slot, slot_count in forced_slots.items():
            mx = 2 if slot == "LEFT_HAND" else 1
            if slot_count > mx:
                msg = f"Too many forced items in position: {slot}"
                raise SolveError(msg)

        for item in (*forced_relics, *forced_epics):
            forced_slots[item.item_slot] -= 1

    else:
        forced_items = []
        forced_relics = []
        forced_epics = []

    AOBJS: collections.defaultdict[str, list[EquipableItem]] = collections.defaultdict(list)

    log.info("Culling items that aren't up to scratch.")

    for item in filter(level_filter, filter(minus_relicepic, OBJS)):
        AOBJS[item.item_slot].append(item)

    for stu in AOBJS.values():
        stu.sort(key=sort_key_initial, reverse=True)

    relics = forced_relics or [
        item
        for item in OBJS
        if item.is_relic and initial_filter(item) and relic_epic_level_filter(item) and item._item_id not in NATION_RELIC_EPIC_IDS
    ]
    epics = forced_epics or [
        item
        for item in OBJS
        if item.is_epic and initial_filter(item) and relic_epic_level_filter(item) and item._item_id not in NATION_RELIC_EPIC_IDS
    ]

    CANIDATES: dict[str, list[EquipableItem]] = {k: v.copy() for k, v in AOBJS.items()}

    def needs_full_sim_key(item: EquipableItem) -> Hashable:
        return (
            item._ap,
            item._range,
            item._mp,
            item._critical_hit,
            item._critical_mastery,
            item._wp,
            item.disables_second_weapon,
        )

    consider_stats = attrgetter("_ap", "_mp", "_range", "disables_second_weapon")
    key_func: Callable[[EquipableItem], Hashable] = lambda i: tuple(map((0).__lt__, consider_stats(i)))

    for _slot, items in CANIDATES.items():
        seen_key: set[Hashable] = set()
        to_rem: list[EquipableItem] = []

        items.sort(key=sort_key, reverse=True)

        if _slot != "LEFT_HAND":
            for item in items:
                key = needs_full_sim_key(item)
                if key in seen_key:
                    to_rem.append(item)
                seen_key.add(key)
        else:
            seen_overflow: set[Hashable] = set()
            for item in items:
                key = needs_full_sim_key(item)
                if key in seen_key:
                    if key in seen_overflow:
                        to_rem.append(item)
                    seen_overflow.add(key)
                seen_key.add(key)

        for item in to_rem:
            try:
                items.remove(item)
            except ValueError:
                pass

        depth = ITEM_SEARCH_DEPTH if _slot != "LEFT_HAND" else ITEM_SEARCH_DEPTH + 3
        if ns.exhaustive:
            depth = len(OBJS)

        if len(items) > depth:
            to_rem = []
            counter: collections.Counter[Hashable] = collections.Counter()
            seen_names_souv: set[Hashable] = set()

            items.sort(key=lambda i: (sort_key(i), i._item_rarity), reverse=True)

            for item in items:
                k = key_func(item)
                sn = (item.name, item.is_souvenir)
                if sn in seen_names_souv:
                    to_rem.append(item)
                    continue

                counter[k] += 1
                if counter[k] > depth:
                    to_rem.append(item)
                else:
                    seen_names_souv.add(sn)

            for item in to_rem:
                items.remove(item)

    relics.sort(key=lambda r: (sort_key(r), r.item_slot), reverse=True)
    relics = ordered_unique_by_key(relics, needs_full_sim_key)
    epics.sort(key=lambda e: (sort_key(e), e.item_slot), reverse=True)
    epics = ordered_unique_by_key(epics, needs_full_sim_key)

    ONEH = [i for i in CANIDATES["FIRST_WEAPON"] if not i.disables_second_weapon]
    TWOH = [i for i in CANIDATES["FIRST_WEAPON"] if i.disables_second_weapon]
    DAGGERS = [i for i in CANIDATES["SECOND_WEAPON"] if i._item_type == 112]

    lw = EquipableItem()
    lw._elemental_mastery = int(HIGH_BOUND * 1.5)
    lw._title_strings[_locale.get()] = "LIGHT WEAPON EXPERT PLACEHOLDER"
    lw._item_lv = HIGH_BOUND
    lw._item_rarity = 4
    lw._item_type = 112
    if LIGHT_WEAPON_EXPERT:
        DAGGERS.append(lw)

    SHIELDS = [] if SKIP_SHIELDS else [i for i in CANIDATES["SECOND_WEAPON"] if i._item_type == 189][:ITEM_SEARCH_DEPTH]

    del CANIDATES["FIRST_WEAPON"]
    del CANIDATES["SECOND_WEAPON"]

    # Tt be reused below

    if WEILD_TYPE_TWO_HANDED:
        canidate_weapons = (*((two_hander,) for two_hander in TWOH),)
    elif SKIP_TWO_HANDED:
        canidate_weapons = (*itertools.product(ONEH, (DAGGERS + SHIELDS)),)
    else:
        canidate_weapons = (*((two_hander,) for two_hander in TWOH), *itertools.product(ONEH, (DAGGERS + SHIELDS)))

    def tuple_expander(seq: Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]) -> Iterator[EquipableItem]:
        for item in seq:
            if isinstance(item, tuple):
                yield from item
            else:
                yield item

    weapon_key_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], Hashable]
    weapon_score_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], float]
    weapon_key_func = lambda w: (*(sum(a) for a in zip(*(needs_full_sim_key(i) for i in tuple_expander(w)))),)
    weapon_score_func = lambda w: sum(map(sort_key_initial, tuple_expander(w)))
    srt_w = sorted(canidate_weapons, key=weapon_score_func, reverse=True)
    canidate_weapons = ordered_unique_by_key(srt_w, weapon_key_func)

    BEST_LIST: list[tuple[float, list[EquipableItem]]] = []

    log.info("Considering the options...")

    extra_pairs: list[tuple[EquipableItem, EquipableItem]] = []

    if not (forced_relics or forced_epics) and (LOW_BOUND <= 200 <= HIGH_BOUND):
        for i in range(4):
            sword_id, ring_id = NATION_RELIC_EPIC_IDS[i], NATION_RELIC_EPIC_IDS[i + 4]
            sword = next((i for i in OBJS if i._item_id == sword_id), None)
            ring = next((i for i in OBJS if i._item_id == ring_id), None)
            if sword and ring:
                extra_pairs.append((sword, ring))

    log.info("Considering some items... This may take a few moments")

    epics.sort(key=sort_key_initial, reverse=True)
    relics.sort(key=sort_key_initial, reverse=True)
    kf: Callable[[EquipableItem], Hashable] = lambda i: (i.item_slot, needs_full_sim_key(i))
    epics = ordered_unique_by_key(epics, kf)
    relics = ordered_unique_by_key(relics, kf)

    re_key_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], Hashable]
    re_score_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], float]
    re_key_func = lambda w: (
        (*(sum(a) for a in zip(*(needs_full_sim_key(i) for i in tuple_expander(w)))),),
        "-".join(sorted(i.item_slot for i in tuple_expander(w))),
    )
    re_score_func = lambda w: sum(map(sort_key_initial, tuple_expander(w)))
    if relics:
        sorted_pairs = sorted((*itertools.product(relics, epics), *extra_pairs), key=re_score_func, reverse=True)
        canidate_re_pairs = ordered_unique_by_key(sorted_pairs, re_key_func)
    else:
        canidate_re_pairs = (
            *itertools.product(relics or [None], epics or [None]),
            *extra_pairs,
        )

    if ns and not ns.exhaustive:
        canidate_re_pairs = canidate_re_pairs[: ns.hard_cap_depth * 2]
        CANIDATES = {k: v[: ns.hard_cap_depth] for k, v in CANIDATES.items()}
        canidate_weapons = canidate_weapons[: ns.hard_cap_depth]

    if ns.dry_run:
        ret: list[EquipableItem] = []
        ret.extend(filter(None, itertools.chain.from_iterable(canidate_re_pairs)))
        for k, v in CANIDATES.items():
            if k in (
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
            ):
                ret.extend(v)

        for weps in canidate_weapons:
            ret.extend(tuple_expander(weps))
        return [(0, ordered_unique_by_key(ret, attrgetter("_item_id")))]

    # everything below this line is performance sensitive, and runtime is based on how much the above
    # managed to reduce the permuations of possible gear.

    base_stats = Stats(ns.baseap, mp=ns.basemp, ra=ns.basera, crit=ns.bcrit) if isinstance(ns, argparse.Namespace) else Stats()

    progress_bar = tqdm.tqdm(canidate_re_pairs, desc="Considering relic epic pairs", unit=" Relic-epic pair")

    for relic, epic in progress_bar:
        if relic and epic:
            if relic.item_slot == epic.item_slot != "LEFT_HAND":
                continue

            if relic.disables_second_weapon and epic.item_slot == "SECOND_WEAPON":
                continue

            if epic.disables_second_weapon and relic.item_slot == "SECOND_WEAPON":
                continue

        partial_score = sort_key(epic) + (sort_key(relic) if relic else 0)

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
        ]

        # This is a slot we allow building without, sets without will be worse ofc...
        if "ACCESSORY" not in CANIDATES:
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

        if relic and relic.item_slot not in REM_SLOTS:
            continue
        if epic and epic.item_slot not in REM_SLOTS:
            continue

        main_hand_disabled = False
        off_hand_disabled = False

        for item in (relic, epic):
            if item is None:
                continue
            if item.item_slot == "FIRST_WEAPON":
                main_hand_disabled = True
                if item.disables_second_weapon:
                    off_hand_disabled = True
            elif item.item_slot == "SECOND_WEAPON":
                off_hand_disabled = True
            else:
                try:
                    REM_SLOTS.remove(item.item_slot)
                except ValueError:
                    pass

        if not (main_hand_disabled and off_hand_disabled):
            REM_SLOTS.append("WEAPONS")

            if main_hand_disabled:
                if WEILD_TYPE_TWO_HANDED:
                    continue
                CANIDATES["WEAPONS"] = [(i,) for i in (*DAGGERS, *SHIELDS)]  # type: ignore
            elif off_hand_disabled:
                if WEILD_TYPE_TWO_HANDED:
                    continue
                CANIDATES["WEAPONS"] = [(i,) for i in ONEH]  # type: ignore
            else:
                CANIDATES["WEAPONS"] = canidate_weapons  # type: ignore

        RING_CHECK_NEEDED = REM_SLOTS.count("LEFT_HAND") > 1

        try:
            cans = [CANIDATES[k] for k in REM_SLOTS]
            cn_c = reduce(mul, map(len, cans), 1) /8
            if RING_CHECK_NEEDED:
                cn_c *= len(CANIDATES["LEFT_HAND"])
        except KeyError as exc:
            log.debug("Constraints may have removed too many items slot: %s", exc.args[0])
            continue

        if cn_c > 5000:
            inner = tqdm.tqdm(itertools.product(*cans), desc="Trying items with that pair", total=cn_c, leave=True)
        else:
            inner = itertools.product(*cans)

        for raw_items in inner:
            items = [*tuple_expander(raw_items), *forced_items]

            if RING_CHECK_NEEDED:
                rings: list[EquipableItem] = [i for i in items if i.item_slot == "LEFT_HAND"]
                r1, r2 = rings
                if r1._item_id == r2._item_id:
                    continue

            statline: Stats = reduce(add, (i.as_stats for i in (relic, epic, *items) if i))
            if statline.ap < AP or statline.mp < MP or statline.wp < WP or statline.ra < RA:
                continue

            crit_chance = statline.crit + BASE_CRIT_CHANCE
            crit_mastery = statline.crit_mastery + BASE_CRIT_MASTERY

            # GLOBAL GAME CONDITION
            if crit_chance < -10:
                continue

            crit_chance = min(crit_chance, 100)

            generated_conditions = [(*item.conditions, item.as_stats) for item in (*items, relic, epic) if item]
            mns, mxs, stats = zip(*generated_conditions)
            mns = reduce(and_, mns, SetMinimums())
            mxs = reduce(and_, mxs, SetMaximums())

            if (mns or mxs) and not generate_filter(base_stats, mns, mxs)(stats):
                continue

            score = sum(sort_key(i) for i in items) + partial_score + BASE_RELEV_MASTERY
            score = (score + (crit_mastery if UNRAVELING else 0)) * ((100 - crit_chance) / 100) + (score + crit_mastery) * (
                crit_chance / 80
            )  # 1.25 * .01, includes crit math

            worst_kept = min(i[0] for i in BEST_LIST) if 0 < len(BEST_LIST) < 3 else 0

            if score > worst_kept:
                filtered = [i for i in (*items, relic, epic) if i]
                filtered.sort(key=lambda i: i._item_id)

                tup = (score, filtered)
                if tup in BEST_LIST:
                    continue
                BEST_LIST.sort(key=itemgetter(0), reverse=True)
                BEST_LIST = BEST_LIST[:5]
                BEST_LIST.append(tup)

    return BEST_LIST


def entrypoint(output: SupportsWrite[str], ns: v1Config | None = None) -> None:
    def write(*args: object, sep: str = " ", end: str = "\n") -> None:
        output.write(f"{sep.join(map(str, args))}{end}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--lv", dest="lv", type=int, choices=list(range(20, 231, 15)), required=True)
    parser.add_argument("--ap", dest="ap", type=int, default=5)
    parser.add_argument("--mp", dest="mp", type=int, default=2)
    parser.add_argument("--wp", dest="wp", type=int, default=0)
    parser.add_argument("--ra", dest="ra", type=int, default=0)
    parser.add_argument("--base-ap", dest="baseap", type=int, default=7)
    parser.add_argument("--base-mp", dest="basemp", type=int, default=4)
    parser.add_argument("--base-range", dest="basera", type=int, default=0)
    parser.add_argument("--num-mastery", type=int, choices=[1, 2, 3, 4], default=3)
    parser.add_argument("--distance", dest="dist", action="store_true", default=False)
    parser.add_argument("--melee", dest="melee", action="store_true", default=False)
    parser.add_argument("--beserk", dest="zerk", action="store_true", default=False)
    parser.add_argument("--rear", dest="rear", action="store_true", default=False)
    parser.add_argument("--heal", dest="heal", action="store_true", default=False)
    parser.add_argument("--unraveling", dest="unraveling", action="store_true", default=False)
    parser.add_argument("--no-skip-shields", dest="skipshields", action="store_false", default=True)
    parser.add_argument("--try-light-weapon-expert", dest="lwx", action="store_true", default=False)
    parser.add_argument("--my-base-crit", dest="bcrit", type=int, default=0)
    parser.add_argument("--my-base-mastery", dest="bmast", type=int, default=0)
    parser.add_argument("--my-base-crit-mastery", dest="bcmast", type=int, default=0)
    parser.add_argument("--forbid", dest="forbid", type=str, action="store", nargs="+")
    parser.add_argument("--id-forbid", dest="idforbid", type=int, action="store", nargs="+")
    parser.add_argument("--id-force", dest="idforce", type=int, action="store", nargs="+")
    parser.add_argument("--name-force", dest="nameforce", type=str, action="store", nargs="+")
    parser.add_argument("--locale", dest="locale", type=str, choices=("en", "pt", "fr", "es"), default="en")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)
    parser.add_argument("--hard-cap-depth", dest="hard_cap_depth", type=int, default=100)
    parser.add_argument("--search-depth", dest="search_depth", type=int, default=1)
    parser.add_argument("--count-negative-zerk", dest="negzerk", type=str, choices=("full", "half", "none"), default="half")
    parser.add_argument("--count-negative-rear", dest="negrear", type=str, choices=("full", "half", "none"), default="none")
    parser.add_argument("--forbid-rarity", dest="forbid_rarity", type=int, choices=list(range(1, 8)), action="store", nargs="+")
    parser.add_argument(
        "--allowed-rarity", dest="allowed_rarities", type=int, choices=list(range(1, 8)), action="store", nargs="+"
    )
    two_h = parser.add_mutually_exclusive_group()
    two_h.add_argument("--use-wield-type-2h", dest="twoh", action="store_true", default=False)
    two_h.add_argument("--skip-two-handed-weapons", dest="skiptwo_hand", action="store_true", default=False)
    parser.add_argument("--exhaustive", dest="exhaustive", default=False, action="store_true")
    parser.add_argument("--tolerance", dest="tolerance", type=int, default=30)


    if ns is None:
        ns = parser.parse_args(namespace=v1Config())

    try:
        result = solve(ns)
    except SolveError as exc:
        msg = exc.args[0]
        write(msg)
        sys.exit(1)

    try:
        score, items = result[0]
    except IndexError:
        write("No sets matching this were found!")
        return

    items.sort(key=lambda i: (not i.is_relic, not i.is_epic, i.item_slot, i.name))
    if ns.dry_run:
        write("Item pool:")
        write(*items, sep="\n")
    else:
        write(f"Best set under constraints has effective mastery {score}:")
        write(*items, sep="\n")


if __name__ == "__main__":
    setup_logging(sys.stdout)
    entrypoint(sys.stdout)
