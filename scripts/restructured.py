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


class FullStats(Struct, frozen=True, gc=True):
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



class SimpleStats(Struct, frozen=True, gc=False):
    ap: int
    mp: int
    wp: int
    ra: int
    crit: int
    crit_mastery: int
    rel_mastery: int
    control: int
    block: int
    fd: int
    heals_performed: int

    def __sub__(self, other: object) -> SimpleStats:
        if not isinstance(other, SimpleStats):
            return NotImplemented

        return SimpleStats(*(operator.sub(s, o) for s, o in zip(astuple(self), astuple(other), strict=True)))

    def __add__(self, other: object) -> SimpleStats:
        if not isinstance(other, SimpleStats):
            return NotImplemented

        return SimpleStats(*(operator.add(s, o) for s, o in zip(astuple(self), astuple(other), strict=True)))


class SetMinimums(Struct, frozen=True, gc=False):
    ap: int = 5
    mp: int = 2
    wp: int = 0
    ra: int = 0
    crit: int = 0
    crit_mastery: int = 0
    rel_mastery: int = 0
    control: int = 0
    block: int = 0
    fd: int = 0
    heals_performed: int = 0


class SetMaximums(Struct, frozen=True, gc=False):
    ap: int = 100
    mp: int = 100
    wp: int = 100
    ra: int = 100
    crit: int = 100
    crit_mastery: int = 100_000
    rel_mastery: int = 100_000
    control: int = 100
    block: int = 100
    fd: int = 100_000
    heals_performed: int = 100_000


def effective_mastery(stats: SimpleStats) -> float:
    # there's a hidden 3% base crit rate in game
    # There's also clamping on crit rate
    crit_rate = max(min(stats.crit + 3, 100), 0)

    fd = 1 + (stats.fd / 100)

    return (
        (stats.rel_mastery * (100 - crit_rate) / 100) * fd
        + ((stats.rel_mastery + stats.crit_mastery) * crit_rate * (fd + .25))
    )

def effective_healing(stats: SimpleStats) -> float:
    """
    We assume a worst case "heals didn't crit" for healing,
    under the philosophy of minimum healing required for safety.

    Crits under this philosophy *may* allow cutting a heal from a rotation on reaction
    making crit a damage stat even in the case of optimizing healing
    """
    return stats.rel_mastery * (1 + (stats.heals_performed / 100))


def apply_w2h(stats: SimpleStats) -> SimpleStats:
    return replace(stats, ap=stats.ap+2, mp=stats.mp-2)


def apply_unravel(stats: SimpleStats) -> SimpleStats:
    if stats.crit >= 40:
        return replace(stats, rel_mastery=stats.rel_mastery+stats.crit_mastery, crit_mastery=0)
    return stats


def apply_elementalism(stats: SimpleStats) -> SimpleStats:
    return replace(stats, fd=stats.fd+30, heals_performed=stats.heals_performed+30)



def generate_filter(
    base_stats: SimpleStats,
    maximums: list[SimpleStats],
    minimums: list[SimpleStats]
) -> Callable[[list[SimpleStats]], bool]:
    min_clamp = SimpleStats(*(max(items) for items in zip(*map(astuple, minimums), strict=True))) - base_stats
    max_clamp = SimpleStats(*(min(items) for items in zip(*map(astuple, maximums), strict=True))) + base_stats

    min_tup = astuple(min_clamp)
    max_tup = astuple(max_clamp)

    def f(item_set: list[SimpleStats]) -> bool:

        stat_tup = astuple(reduce(operator.add, item_set))

        return all(mn <= s <= mx for mn, s, mx in zip(min_tup, stat_tup, max_tup, strict=True))
    
    return f
