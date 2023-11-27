"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import argparse
import collections
import itertools
import logging
import statistics
import sys
from collections.abc import Callable, Hashable, Iterable, Iterator
from functools import lru_cache, partial, reduce
from operator import add, and_, attrgetter, itemgetter
from typing import TYPE_CHECKING, Final, Protocol, TypeVar

from .item_conditions import get_item_conditions
from .object_parsing import EquipableItem, get_all_items, set_locale
from .restructured_types import ElementsEnum, SetMaximums, SetMinimums, Stats, apply_w2h, v1Config
from .utils import only_once
from .wakforge_buildcodes import build_code_from_items

# TODO: possibly enable this for pyodide use? want to look into the overhead more
if "pyodide" not in sys.modules:
    import tqdm
    from tqdm.contrib.itertools import product as _tqdm_product  # type: ignore

    tqdm_product = partial(_tqdm_product, desc="Trying items with that pair", leave=False)
    if TYPE_CHECKING:
        tqdm_product = itertools.product

else:
    tqdm = None
    tqdm_product = None

T = TypeVar("T")

log = logging.getLogger("solver")


T_contra = TypeVar("T_contra", contravariant=True)


class SupportsWrite(Protocol[T_contra]):
    def write(self, s: T_contra, /) -> object:
        ...


ALWAYS_SIMMED = "ap", "mp", "ra", "wp", "critical_hit", "critical_mastery"


@only_once
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


def solve(ns: v1Config, use_tqdm: bool = False) -> list[tuple[float, list[EquipableItem]]]:
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

        score += item.elemental_mastery
        if ns.melee:
            score += item.melee_mastery
        if ns.dist:
            score += item.distance_mastery
        if ns.zerk:
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

        if ns.rear:
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
            score += item.mastery_1_element
        if ns.num_mastery <= 2:
            score += item.mastery_2_elements
        if ns.num_mastery <= 3:
            score += item.mastery_3_elements

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
            score += element_vals / n

        return score

    score_key = lru_cache(_score_key)

    @lru_cache
    def crit_score_key(item: EquipableItem | None) -> float:
        if item is None:
            return 0
        base_score = score_key(item)
        return base_score + ((item.critical_hit + base_stats.critical_hit + 11) / 80) * base_score

    def has_currently_unhandled_item_condition(item: EquipableItem) -> bool:
        return any(i.unhandled() for i in get_item_conditions(item))

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

    stat_mins = ns.stat_minimums or SetMinimums(ap=ns.ap, mp=ns.mp, wp=ns.wp, ra=ns.ra)
    base_stats = ns.base_stats or Stats(
        ns.baseap,
        mp=ns.basemp,
        ra=ns.basera,
        wp=ns.bawewp,
        critical_hit=ns.bcrit,
        critical_mastery=ns.bcmast,
        elemental_mastery=ns.bmast,
    )

    BASE_STAT_SCORE = _score_key(base_stats)

    def initial_filter(item: EquipableItem) -> bool:
        return bool(
            (item.item_id not in FORBIDDEN)
            and (item.name not in FORBIDDEN_NAMES)
            and (not has_currently_unhandled_item_condition(item))
            and ((item.item_rarity in allowed_rarities) or (item.item_slot in ("MOUNT", "PET")))
        )

    def level_filter(item: EquipableItem) -> bool:
        if item.item_slot in ("MOUNT", "PET"):
            return True
        return ns.lv >= item.item_lv >= LOW_BOUND

    def relic_epic_level_filter(item: EquipableItem) -> bool:
        """The unreasonable effectiveness of these two rings extends them a bit"""
        if item.item_id == 9723:  # gelano
            return 140 >= ns.lv >= 65
        if item.item_id == 27281:  # bagus shushu
            return 185 >= ns.lv >= 125
        return ns.lv >= item.item_lv >= LOW_BOUND

    def minus_relicepic(item: EquipableItem) -> bool:
        return not (item.is_epic or item.is_relic)

    forced_slots: collections.Counter[str] = collections.Counter()
    original_forced_counts: collections.Counter[str] | None = None
    if ns and (ns.idforce or ns.nameforce):
        _fids = ns.idforce or ()
        _fns = ns.nameforce or ()

        forced_items = [i for i in ALL_OBJS if i.item_id in _fids]
        # Handle names a little differently to avoid an issue with duplicate names
        forced_by_name = [i for i in ALL_OBJS if i.name in _fns]
        forced_by_name.sort(key=score_key, reverse=True)
        forced_by_name = ordered_keep_by_key(forced_by_name, key=attrgetter("name", "item_slot"), k=1)
        forced_items.extend(forced_by_name)

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

        forced_epics = [*(i for i in forced_items if i.is_epic), *forced_ring]
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
            forced_items.remove(item)

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

    OBJS: Final[list[EquipableItem]] = list(filter(initial_filter, ALL_OBJS))
    del ALL_OBJS

    AOBJS: collections.defaultdict[str, list[EquipableItem]] = collections.defaultdict(list)

    log.info("Culling items that aren't up to scratch.")

    for item in filter(level_filter, filter(minus_relicepic, OBJS)):
        AOBJS[item.item_slot].append(item)

    for stu in AOBJS.values():
        stu.sort(key=score_key, reverse=True)

    relics = forced_relics or [
        item
        for item in OBJS
        if item.is_relic and initial_filter(item) and relic_epic_level_filter(item) and item.item_id not in NATION_RELIC_EPIC_IDS
    ]
    epics = forced_epics or [
        item
        for item in OBJS
        if item.is_epic and initial_filter(item) and relic_epic_level_filter(item) and item.item_id not in NATION_RELIC_EPIC_IDS
    ]

    solve_CANIDATES: dict[str, list[EquipableItem]] = {k: v.copy() for k, v in AOBJS.items()}

    def needs_full_sim_key(item: EquipableItem) -> Hashable:
        keys = {"disables_second_weapon", *ALWAYS_SIMMED}
        return attrgetter(*keys)(item)

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

    adj_getter = attrgetter(*stat_mins.get_sim_keys())

    def adj_func(item: EquipableItem) -> float:
        mins = tuple(i - j for i, j in zip(adj_getter(stat_mins), adj_getter(base_stats), strict=True))
        perc_contr = [(i + 1) / (j or 1) for i, j in zip(adj_getter(item), mins, strict=True)]
        return sum(perc_contr) / len(perc_contr)

    # TODO: Break this loop out into dedicated function for pruning item pool
    for items in (solve_ONEH, solve_TWOH, solve_DAGGERS, *solve_CANIDATES.values()):
        if not items:
            continue
        slot = items[0].item_slot

        items.sort(key=score_key, reverse=True)
        inplace_ordered_keep_by_key(items, attrgetter("name", "is_souvenir"))

        dist = statistics.NormalDist.from_samples(adj_func(i) for i in items) if len(items) > 1 else None

        def adjusted_key(item: EquipableItem, dist: statistics.NormalDist | None = dist) -> float:
            st = crit_score_key(item)
            if dist is None:
                return st
            try:
                adj = dist.zscore(adj_func(item))
            except statistics.StatisticsError:  # zscore when sigma = 0
                adj = 0
            if adj:
                return st + (adj * st * 0.1)
            return st

        items.sort(key=adjusted_key, reverse=True)

        k = 2 if slot == "LEFT_HAND" else 1
        uniq = ordered_keep_by_key(items, needs_full_sim_key, k)

        if not ns.exhaustive:
            items.sort(key=lambda i: (i in uniq, adjusted_key(i)), reverse=True)
            adaptive_depth = ns.search_depth - 1 + k

            if ns.lv < 50:  # Needed due to item design and low level -wp items
                adaptive_depth += 2

            bck = items.copy()
            bck.sort(key=adjusted_key, reverse=True)
            inplace_ordered_keep_by_key(bck, needs_full_sim_key)
            del items[adaptive_depth:]

            for val in (0, 1):
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
                    if len([i for i in items if all(s >= val for s in attrgetter("ap", "mp", "ra", "wp")(i))]) >= k:
                        break

            uniq = ordered_keep_by_key(items, needs_full_sim_key, k)
            for i in items[::-1]:
                if i not in uniq:
                    items.remove(i)
        else:
            # simply keep the uniq without trimming then...
            for i in items[::-1]:
                if i not in uniq:
                    items.remove(i)

    relics.sort(key=lambda r: (score_key(r), r.item_slot), reverse=True)
    inplace_ordered_keep_by_key(relics, needs_full_sim_key)
    epics.sort(key=lambda e: (score_key(e), e.item_slot), reverse=True)
    inplace_ordered_keep_by_key(epics, needs_full_sim_key)

    if ns.lwx:
        solve_DAGGERS.append(EquipableItem(-2, ns.lv, 4, 112, elemental_mastery=int(ns.lv * 1.5)))

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

    def tuple_expander(seq: Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]) -> Iterator[EquipableItem]:
        for item in seq:
            if isinstance(item, tuple):
                yield from item
            else:
                yield item

    weapon_key_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], Hashable]
    weapon_score_func: Callable[[Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]], float]
    weapon_key_func = lambda w: (
        isinstance(w, tuple),
        *(sum(a) for a in zip(*(needs_full_sim_key(i) for i in tuple_expander(w)))),
    )
    weapon_score_func = lambda w: sum(map(score_key, tuple_expander(w)))
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

    def re_key_func(pair: tuple[EquipableItem | None, EquipableItem | None]) -> Hashable:
        if not any(pair):
            return 0
        disables_second = any(i.disables_second_weapon for i in pair if i)
        positions = [i.item_slot for i in pair if i]
        pos_key = "-".join(sorted(positions))
        re_s = [i.as_stats() for i in pair if i]
        sc = re_s[0]
        if len(re_s) > 1:
            sc = sc + re_s[1]
        ks = attrgetter(*ALWAYS_SIMMED)(sc)
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
    pairs = [*itertools.product(relics or [None], epics or [None]), *extra_pairs]
    pairs.sort(key=re_score_key, reverse=True)
    canidate_re_pairs = ordered_keep_by_key(pairs, re_key_func)
    pairs.sort(key=lambda p: re_score_key(p)[1:], reverse=True)

    if ns and not ns.exhaustive:
        per_item_factor: Callable[[object, object], int] = lambda llv, lls: 2 if lls == "LEFT_HAND" else 1
        canidate_re_pairs = canidate_re_pairs[: ns.hard_cap_depth]
        solve_CANIDATES = {k: v[: ns.search_depth + per_item_factor(ns.lv, k)] for k, v in solve_CANIDATES.items()}
        canidate_weapons = canidate_weapons[: int(ns.hard_cap_depth / 2)]

    if ns.dry_run:
        ret: list[EquipableItem] = []
        ret.extend(filter(None, itertools.chain.from_iterable(canidate_re_pairs)))
        ret.extend(forced_items)
        for k, v in solve_CANIDATES.items():
            if "WEAPON" not in k:
                ret.extend(v)

        for weps in canidate_weapons:
            ret.extend(tuple_expander(weps))
        return [(0, ordered_keep_by_key(ret, attrgetter("item_id")))]

    # everything below this line is performance sensitive, and runtime is based on how much the above
    # managed to reduce the permuations of possible gear.

    maybe_progress_bar: Iterable[tuple[EquipableItem | None, EquipableItem | None]]
    if use_tqdm and tqdm:
        maybe_progress_bar = tqdm.tqdm(canidate_re_pairs, desc="Considering relic epic pairs", unit=" Relic-epic pair")
    else:
        maybe_progress_bar = canidate_re_pairs

    solve_CANIDATES.pop("WEAPONS", None)

    for relic, epic in maybe_progress_bar:
        if relic and epic:
            if relic.item_slot == epic.item_slot != "LEFT_HAND":
                continue

            if relic.disables_second_weapon and epic.item_slot == "SECOND_WEAPON":
                continue

            if epic.disables_second_weapon and relic.item_slot == "SECOND_WEAPON":
                continue

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
            continue
        if epic and epic.item_slot not in REM_SLOTS and "WEAPON" not in epic.item_slot:
            continue

        main_hand_disabled = False
        off_hand_disabled = False

        for item in (relic, epic, *forced_items):
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
                    pass

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
                weapons = canidate_weapons

            weapons.sort(key=weapon_score_func, reverse=True)

        try:
            k = REM_SLOTS.count("LEFT_HAND")
            ring_pairs = list(itertools.combinations(solve_CANIDATES["LEFT_HAND"], k)) if k else ()
            cans = [ring_pairs, *(solve_CANIDATES[k] for k in REM_SLOTS if k not in ("LEFT_HAND", "WEAPONS"))]
            if "WEAPONS" in REM_SLOTS:
                cans.append(weapons)
        except KeyError as exc:
            log.debug("Constraints may have removed too many items slot: %s", exc.args[0])
            continue

        gen_func = tqdm_product if use_tqdm and tqdm_product else itertools.product

        for raw_items in gen_func(*filter(None, cans)):
            items = [*tuple_expander(raw_items), *forced_items]

            statline: Stats = reduce(add, (i.as_stats() for i in (relic, epic, *items) if i), base_stats)
            if ns.twoh and any(i.disables_second_weapon for i in items):
                statline = apply_w2h(statline)

            # GLOBAL GAME CONDITION
            if statline.critical_hit < -10:
                continue

            generated_conditions = [get_item_conditions(item) for item in (*items, relic, epic) if item]
            mns, mxs = zip(*generated_conditions)
            mns = reduce(and_, mns, stat_mins)
            mxs = reduce(and_, mxs, SetMaximums())

            if not statline.is_between(mns, mxs):
                continue
            UNRAVEL_ACTIVE = ns.unraveling and statline.critical_hit >= 40

            crit_chance = max(min(statline.critical_hit + 3, 100), 0)  # engine crit rate vs stat

            score = sum(score_key(i) for i in (*items, relic, epic)) + BASE_STAT_SCORE
            score = (
                (score + (statline.critical_mastery if UNRAVEL_ACTIVE else 0)) * ((100 - crit_chance) / 100)
                + (score + statline.critical_mastery) * (crit_chance / 80)  # 1.25 * .01, includes crit math
            )

            worst_kept = min(i[0] for i in solve_BEST_LIST) if 0 < len(solve_BEST_LIST) < 3 else 0

            if score > worst_kept:
                filtered = [i for i in (*items, relic, epic) if i]
                filtered.sort(key=lambda i: i.item_id)

                tup = (score, filtered)
                solve_BEST_LIST.sort(key=itemgetter(0), reverse=True)
                solve_BEST_LIST = solve_BEST_LIST[:5]
                solve_BEST_LIST.append(tup)

    return solve_BEST_LIST


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
    parser.add_argument("--search-depth", dest="search_depth", type=int, default=2)
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
        result = solve(ns, use_tqdm=True)
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

        build = build_code_from_items(ns.lv, items)
        write("Wakforge compatible build code (items and level only):", build, sep="\n")


if __name__ == "__main__":
    setup_logging(sys.stdout)
    entrypoint(sys.stdout)
