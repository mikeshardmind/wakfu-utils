"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import argparse
import builtins

# pyright: reportPrivateUsage=false
# pyright: reportConstantRedefinition=false
import collections
import itertools
import logging
import sys
from collections.abc import Hashable, Iterable, Iterator
from functools import lru_cache
from operator import itemgetter
from pprint import pprint as p_print

from object_parsing import EquipableItem, _locale


def solve(
    ns: argparse.Namespace | None = None, no_print_log: bool = False,
) -> list[tuple[float, str, list[EquipableItem]]]:
    """Still has some debug stuff in here, will be refactoring this all later."""

    log = logging.getLogger("Set Builder")

    def null_printer(*args: object, **kwargs: object) -> object:
        pass

    if no_print_log:
        log.addHandler(logging.NullHandler())
        aprint = pprint = null_printer
    else:
        aprint = builtins.print
        pprint = p_print
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="%",
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(logging.INFO)

    # ## Everything in this needs abstracting into something
    # that can handle user input and be more dynamic.
    # ## Could benefit from some optimizations here and there.

    UNOBTAINABLE = [15296]

    ALL_OBJS = [i for i in EquipableItem.from_bz2_bundled() if i._item_id not in UNOBTAINABLE]

    # Stat minimums
    # 7ish
    AP = 5
    MP = 1
    RA = 2
    WP = 0
    CRIT = -10

    BASE_CRIT_CHANCE = 3 + 20
    BASE_CRIT_MASTERY = 26 * 4
    BASE_RELEV_MASTERY = 40 * 8 + 5 * 6 + 40
    HIGH_BOUND = 185
    LOW_BOUND = HIGH_BOUND - 30
    LIGHT_WEAPON_EXPERT = True
    SKIP_SHIELDS = True
    UNRAVELING = False
    ITEM_SEARCH_DEPTH = 3  # this increases time significantly to increase, increase with care.
    WEILD_TYPE_TWO_HANDED = False

    if ns is not None:
        AP = ns.ap
        MP = ns.mp
        RA = ns.ra
        WP = ns.wp
        HIGH_BOUND = ns.lv
        LOW_BOUND = HIGH_BOUND - 30
        UNRAVELING = ns.unraveling
        SKIP_SHIELDS = ns.skipshields
        LIGHT_WEAPON_EXPERT = ns.lwx
        WEILD_TYPE_TWO_HANDED = ns.twoh
        BASE_CRIT_CHANCE = 3 + ns.bcrit
        BASE_CRIT_MASTERY = ns.bcmast
        BASE_RELEV_MASTERY = ns.bmast

    # TODO: ELEMENTAL_CONCENTRATION = False

    if UNRAVELING:
        CRIT = min(CRIT, 40)

    if WEILD_TYPE_TWO_HANDED:
        AP -= 2
        MP += 2

    @lru_cache
    def sort_key(item: EquipableItem) -> int:
        if ns is not None:
            score = item._elemental_mastery
            if ns.melee:
                score += item._melee_mastery
            if ns.dist:
                score += item._distance_mastery
            if ns.zerk:
                score += item._berserk_mastery
            if ns.rear:
                score += item._rear_mastery
            if ns.heal:
                score += item._healing_mastery

            if ns.num_mastery == 1:
                score += item._mastery_1_element
            if ns.num_mastery <= 2:
                score += item._mastery_2_elements
            if ns.num_mastery <= 3:
                score += item._mastery_3_elements

            return score

        return (
            item._elemental_mastery
            # + item._mastery_1_element
            # + item._mastery_2_elements
            + item._mastery_3_elements
            + item._distance_mastery
            # + item._healing_mastery
            # + item._melee_mastery
            # + item._rear_mastery
        )

    def sort_key_initial(item: EquipableItem) -> float:
        return (
            sort_key(item)
            + 100 * (max(item._mp + item._ap, 0))
            + 50 * (max(item._wp + item._range, 0))
            + ((BASE_CRIT_CHANCE + 20) / 100) * item._critical_mastery
        )

    NATIONS = ("Bonta", "Brakmar", "Sufokia", "Amakna")
    WEIRD_ONES = ("Ring", "Sword")

    EXTRA_ITEMS = [f"{n} {t}" for (n, t) in itertools.product(NATIONS, WEIRD_ONES)]

    FORBIDDEN = (
        [  # noqa: RUF005
            # Ankama doesn't include conditions in item data, need special handling for some items later
            "Maj'Hic Cloak",
            "Worn to a Shadow",
            "Mocking Cap",
            "Kroraging Epaulettes",
            "Belt of Shadows",
            "Prismatic Dofus",
            "Shadowed Boots",
            "Shademail",
            "Dehydrated Breastplate",
            "Brrr Belt",
            "Bubuckle",
            "Spicy Belt",
            "Trool Warrior Spikes",
            "Breastplate of Shadows",
            "Jeering Epaulettes",
            "Cape Hillary",
            "Salty Cape",
            "Kroraging Epaulettes",
            "DigiArv Belt",
            "Amon Amarth Breastplate",
            "Broken Sword",  # pathalogical decision making with -res item undesirable
            "Ancient Trool Warrior Spikes",
            "Beach Bandage",  # pathalogical decision making with -res item undesirable
        ]
        + EXTRA_ITEMS
        # and things that aren't marked unobtainable, but appear to be
        + ["Fuzzy Cards", "Nemotilus Harpoon", "Nemotilus Bolt Screw"]
    )

    if ns and ns.forbid:
        FORBIDDEN.extend(ns.forbid)

    def initial_filter(item: EquipableItem) -> bool:
        return bool(
            HIGH_BOUND >= item._item_lv >= LOW_BOUND
            and (not (item.is_epic or item.is_relic))
            and (item.name not in FORBIDDEN)
            and ("Makabra" not in (item.name or ""))
        )

    OBJS = list(filter(initial_filter, ALL_OBJS))

    AOBJS: collections.defaultdict[str, list[EquipableItem]] = collections.defaultdict(list)

    log.info("Culling items that aren't up to scratch.")

    for item in filter(initial_filter, OBJS):
        AOBJS[item.item_slot].append(item)

    for stu in AOBJS.values():
        stu.sort(key=sort_key_initial, reverse=True)

    relics = [
        item
        for item in ALL_OBJS
        if item.is_relic
        and (
            (HIGH_BOUND >= item._item_lv >= LOW_BOUND and item.name not in FORBIDDEN)
            or (item.name == "Gelano" and 155 >= HIGH_BOUND >= 65)
        )
    ] or [None]
    epics = [
        item
        for item in ALL_OBJS
        if item.is_epic
        and (
            (HIGH_BOUND >= item._item_lv >= LOW_BOUND and item.name not in FORBIDDEN)
            or (item.name == "Bagus Shushu" and 185 >= HIGH_BOUND >= 125)
        )
    ]

    CANIDATES: dict[str, list[EquipableItem]] = {k: v[:ITEM_SEARCH_DEPTH] for k, v in AOBJS.items()}

    rings = AOBJS["LEFT_HAND"]
    filtered_rings: list[EquipableItem] = []
    for ring in rings:
        if any((ring.name == r.name) and (ring._item_rarity in (1, 2, 3, 4)) for r in filtered_rings):
            continue
        filtered_rings.append(ring)
        if len(filtered_rings) >= ITEM_SEARCH_DEPTH:
            break

    if filtered_rings:
        CANIDATES["LEFT_HAND"] = filtered_rings

    try:
        CANIDATES["ACCESSORY"] = CANIDATES["ACCESSORY"][:ITEM_SEARCH_DEPTH]
    except KeyError:
        pass  # accessories dont exist at all levels

    # Weapons need a bit of special handling
    # to prevent 2H weapons from sorting out 1Hs
    ONEH = [i for i in AOBJS["FIRST_WEAPON"] if not i.disables_second_weapon][:ITEM_SEARCH_DEPTH]

    TWOH = [i for i in AOBJS["FIRST_WEAPON"] if i.disables_second_weapon][:ITEM_SEARCH_DEPTH]

    # Same with breastplates....
    AP_BPS = [i for i in AOBJS["CHEST"] if i._ap == 1][:ITEM_SEARCH_DEPTH]
    MP_BPS = [i for i in AOBJS["CHEST"] if i._mp == 1][:ITEM_SEARCH_DEPTH]

    seen_key: set[Hashable] = set()
    _seen_add = seen_key.add

    # with/without range
    for item_key in ("HEAD", "NECK"):
        wr: list[EquipableItem] = []
        wor: list[EquipableItem] = []
        for i in CANIDATES[item_key]:
            if i._range > 0:
                wr.append(i)
            else:
                wor.append(i)

        CANIDATES[item_key] = wr[:ITEM_SEARCH_DEPTH] + wor[:ITEM_SEARCH_DEPTH]

    CANIDATES["CHEST"] = [  # keep best few of each type of chest
        i
        for i in (*AP_BPS, *MP_BPS, *list(AOBJS["CHEST"])[:ITEM_SEARCH_DEPTH])
        if not (i in seen_key or _seen_add(i))
    ]  # todo: similar treatment for cloaks, weapons, boots for 200+

    # Shields and daggers diverge in a way that makes them need it too
    # if a shield is overall best in slot,
    # but a dagger hits the benchmarks more comfortably...

    def needs_full_sim_key(item: EquipableItem) -> tuple[int, ...]:
        return (item._ap, item._mp, item._critical_hit, item._critical_mastery, item._wp)

    kept_rings = CANIDATES["LEFT_HAND"].copy()

    for _slot, items in CANIDATES.items():
        seen_key: set[Hashable] = set()
        to_rem: list[EquipableItem] = []

        items.sort(key=sort_key, reverse=True)

        for item in items:
            key = needs_full_sim_key(item)
            if key in seen_key:
                to_rem.append(item)
            seen_key.add(key)

        for item in to_rem:
            try:
                items.remove(item)
            except ValueError:
                pass

    # ring diversity
    kcounts: collections.Counter[Hashable] = collections.Counter()
    kept_rings.sort(key=sort_key, reverse=True)
    to_rem = []
    for ring in kept_rings:
        key = needs_full_sim_key(ring)
        kcounts[key] += 1
        if kcounts[key] > 2:
            to_rem.append(ring)
    CANIDATES["LEFT_HAND"] = [ring for ring in kept_rings if ring not in to_rem]

    DAGGERS = [i for i in AOBJS["SECOND_WEAPON"] if i._item_type == 112][:ITEM_SEARCH_DEPTH]

    if LIGHT_WEAPON_EXPERT:
        lw = EquipableItem()
        lw._elemental_mastery = int(HIGH_BOUND * 1.5)
        lw._title_strings[_locale.get()] = "LIGHT WEAPON EXPERT PLACEHOLDER"
        lw._item_lv = HIGH_BOUND
        lw._item_rarity = 4
        lw._item_type = 112
        DAGGERS.append(lw)

    SHIELDS = [] if SKIP_SHIELDS else [i for i in AOBJS["SECOND_WEAPON"] if i._item_type == 189][:ITEM_SEARCH_DEPTH]

    del CANIDATES["FIRST_WEAPON"]
    del CANIDATES["SECOND_WEAPON"]

    # Tt be reused below
    canidate_weapons = (*((two_hander,) for two_hander in TWOH), *itertools.product(ONEH, (DAGGERS + SHIELDS)))

    if WEILD_TYPE_TWO_HANDED:
        canidate_weapons = (*((two_hander,) for two_hander in TWOH),)

    def tuple_expander(seq: Iterable[tuple[EquipableItem, EquipableItem] | EquipableItem]) -> Iterator[EquipableItem]:
        for item in seq:
            if isinstance(item, tuple):
                yield from item
            else:
                yield item

    BEST_LIST: list[tuple[float, str, list[EquipableItem]]] = []

    log.info("Considering the options...")

    extra_pairs: list[tuple[EquipableItem, EquipableItem]] = []

    if LOW_BOUND <= 200 <= HIGH_BOUND:
        for n in NATIONS:
            if n == "Brakmar":
                relic = next(i for i in ALL_OBJS if i.name == f"{n} Sword" and i.is_relic)
                epic = next(i for i in ALL_OBJS if i.name == f"{n} Ring" and i.is_epic)
                extra_pairs.append((relic, epic))

    aprint("Considering some items... This may take a few moments")
    if ns is None:
        pprint(
            {
                k: v
                for k, v in CANIDATES.items()
                if k
                in (
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
                )
            }
        )

        if relics:
            aprint("Considering relics:")
            pprint(relics, width=120)
        if epics:
            aprint("Considering epics:")
            pprint(epics, width=120)

        if TWOH:
            aprint("Considering two-handed weapons:", *TWOH, sep=" ")
        if ONEH:
            aprint("Considering one-handed weapons:", *ONEH, sep=" ")
        if z := DAGGERS + SHIELDS:
            aprint("Considering off-hands:", *z, sep=" ")

    number = len(relics) * len(epics) + len(extra_pairs)

    for idx, (relic, epic) in enumerate((*itertools.product(relics, epics), *extra_pairs), 0):
        prog = int(idx * 100 / number)
        print(f"Progress: {prog}%")
        if relic is not None:
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
                REM_SLOTS.remove(item.item_slot)

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

        for raw_items in itertools.product(*[CANIDATES[k] for k in REM_SLOTS]):
            items = list(tuple_expander(raw_items))

            if RING_CHECK_NEEDED:
                rings: list[EquipableItem] = [i for i in items if i.item_slot == "LEFT_HAND"]
                r1, r2 = rings
                if r1._item_id == r2._item_id:
                    continue

            if (relic._ap if relic else 0) + epic._ap + sum(i._ap for i in items) < AP:
                continue

            if (relic._mp if relic else 0) + epic._mp + sum(i._mp for i in items) < MP:
                continue

            if (relic._wp if relic else 0) + epic._wp + sum(i._wp for i in items) < WP:
                continue

            if (relic._range if relic else 0) + epic._range + sum(i._range for i in items) < RA:
                continue

            crit_chance = (
                (relic._critical_hit if relic else 0)
                + epic._critical_hit
                + sum(i._critical_hit for i in items)
                + BASE_CRIT_CHANCE
            )

            crit_mastery = (
                (relic._critical_mastery if relic else 0)
                + epic._critical_mastery
                + sum(i._critical_mastery for i in items)
                + BASE_CRIT_MASTERY
            )

            if crit_chance < CRIT:
                continue

            crit_chance = min(crit_chance, 100)

            score = sum(sort_key(i) for i in items) + partial_score + BASE_RELEV_MASTERY
            score = (score + (crit_mastery if UNRAVELING else 0)) * ((100 - crit_chance) / 100) + (
                score + crit_mastery
            ) * (
                crit_chance / 80
            )  # 1.25 * .01, includes crit math

            worst_kept = min(i[0] for i in BEST_LIST) if 0 < len(BEST_LIST) < 3 else 0

            if score > worst_kept:
                components: list[str] = []
                if relic:
                    components.append(f"Relic: {relic}")
                if epic:
                    components.append(f"Epic: {epic}")

                for item in sorted(items, key=lambda item: item.item_slot):
                    components.append(f"{item.item_type_name.title()}: {item}")

                text_repr = "\n".join(components)

                filtered = [i for i in items if i]
                if relic:
                    filtered.append(relic)
                if epic:
                    filtered.append(epic)
                filtered.sort(key=lambda i: i._item_id)

                tup = (score, text_repr, filtered)
                if tup in BEST_LIST:
                    continue
                BEST_LIST.sort(key=itemgetter(0), reverse=True)
                BEST_LIST = BEST_LIST[:5]
                BEST_LIST.append(tup)
    try:
        (score, info, _items) = BEST_LIST[0]
    except IndexError:
        aprint("No sets matching this were found!")
    else:
        aprint("Done searching, here's my top pick\n")
        aprint(f"Effective average mastery: {score:3g}\nItems:\n{info}\n")

    return BEST_LIST


def entrypoint() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--lv", dest="lv", type=int, choices=list(range(20, 231, 15)), required=True)
    parser.add_argument("--ap", dest="ap", type=int, default=5)
    parser.add_argument("--mp", dest="mp", type=int, default=2)
    parser.add_argument("--wp", dest="wp", type=int, default=0)
    parser.add_argument("--ra", dest="ra", type=int, default=0)
    parser.add_argument("--num-mastery", type=int, choices=[1, 2, 3, 4], default=2)
    parser.add_argument("--distance", dest="dist", action="store_true", default=False)
    parser.add_argument("--melee", dest="melee", action="store_true", default=False)
    parser.add_argument("--beserk", dest="zerk", action="store_true", default=False)
    parser.add_argument("--rear", dest="rear", action="store_true", default=False)
    parser.add_argument("--heal", dest="heal", action="store_true", default=False)
    parser.add_argument("--unraveling", dest="unraveling", action="store_true", default=False)
    parser.add_argument("--no-skip-shields", dest="skipshields", action="store_false", default=True)
    parser.add_argument("--try-light-weapon-expert", dest="lwx", action="store_true", default=False)
    parser.add_argument("--use-wield-type-2h", dest="twoh", action="store_true", default=False)
    parser.add_argument("--my-base-crit", dest="bcrit", type=int, default=0)
    parser.add_argument("--my-base-mastery", dest="bmast", type=int, default=0)
    parser.add_argument("--my-base-crit-mastery", dest="bcmast", type=int, default=0)
    parser.add_argument("--forbid", dest="forbid", type=str, action="extend", nargs="+")

    solve(parser.parse_args())


if __name__ == "__main__":
    entrypoint()
