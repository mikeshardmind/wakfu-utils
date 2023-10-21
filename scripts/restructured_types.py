"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
# intentional restructuring the problem space a bit from solver.py
# Goal of simplifying the problem of allowing complex conditions to be expressible and performant

from __future__ import annotations

import operator
from collections.abc import Callable
from functools import reduce

from msgspec import Struct
from msgspec.structs import astuple, replace


class Stats(Struct, frozen=True, gc=True):
    ap: int
    mp: int
    wp: int
    ra: int
    crit: int
    crit_mastery: int
    elemental_mastery: int
    one_element_mastery: int
    two_element_mastery: int
    three_element_mastery: int
    distance_mastery: int
    rear_mastery: int
    heal_mastery: int
    beserk_mastery: int
    melee_mastery: int
    control: int
    block: int
    fd: int
    heals_performed: int
    lock: int
    dodge: int


    def __sub__(self, other: object) -> Stats:
        if not isinstance(other, Stats):
            return NotImplemented

        return Stats(*(operator.sub(s, o) for s, o in zip(astuple(self), astuple(other), strict=True)))

    def __add__(self, other: object) -> Stats:
        if not isinstance(other, Stats):
            return NotImplemented

        return Stats(*(operator.add(s, o) for s, o in zip(astuple(self), astuple(other), strict=True)))


DUMMY_MIN: int = -1_000_000
DUMMY_MAX: int = 1_000_000

class SetMinimums(Stats, frozen=True, gc=False):
    ap: int = 5
    mp: int = 2
    wp: int = 0
    ra: int = 0
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


class SetMaximums(Stats, frozen=True, gc=False):
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


def effective_mastery(stats: Stats, rel_mastery_key: Callable[[Stats], int]) -> float:
    # there's a hidden 3% base crit rate in game
    # There's also clamping on crit rate
    crit_rate = max(min(stats.crit + 3, 100), 0)

    fd = 1 + (stats.fd / 100)

    rel_mastery = rel_mastery_key(stats)

    return (
        (rel_mastery * (100 - crit_rate) / 100) * fd
        + ((rel_mastery + stats.crit_mastery) * crit_rate * (fd + .25))
    )

def effective_healing(stats: Stats, rel_mastery_key: Callable[[Stats], int]) -> float:
    """
    We assume a worst case "heals didn't crit" for healing,
    under the philosophy of minimum healing required for safety.

    Crits under this philosophy *may* allow cutting a heal from a rotation on reaction
    making crit a damage stat even in the case of optimizing healing
    """
    return rel_mastery_key(stats) * (1 + (stats.heals_performed / 100))


def apply_w2h(stats: Stats) -> Stats:
    return replace(stats, ap=stats.ap+2, mp=stats.mp-2)


def apply_unravel(stats: Stats) -> Stats:
    if stats.crit >= 40:
        return replace(stats, elemental_mastery=stats.elemental_mastery+stats.crit_mastery, crit_mastery=0)
    return stats


def apply_elementalism(stats: Stats) -> Stats:
    if (stats.one_element_mastery == stats.two_element_mastery == 0) and stats.three_element_mastery != 0:
        return replace(stats, fd=stats.fd+30, heals_performed=stats.heals_performed+30)
    return stats



def generate_filter(
    base_stats: Stats,
    maximums: list[Stats],
    minimums: list[Stats]
) -> Callable[[list[Stats]], bool]:
    min_clamp = Stats(*(max(items) for items in zip(*map(astuple, minimums), strict=True))) - base_stats
    max_clamp = Stats(*(min(items) for items in zip(*map(astuple, maximums), strict=True))) + base_stats

    min_tup = astuple(min_clamp)
    max_tup = astuple(max_clamp)

    def f(item_set: list[Stats]) -> bool:

        stat_tup = astuple(reduce(operator.add, item_set))

        return all(mn <= s <= mx for mn, s, mx in zip(min_tup, stat_tup, max_tup, strict=True))
    
    return f
