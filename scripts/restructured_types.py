"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
# intentional restructuring the problem space a bit from solver.py
# Goal of simplifying the problem of allowing complex conditions to be expressible and performant

from __future__ import annotations

import enum
import operator
from collections.abc import Callable
from functools import reduce
from itertools import chain

from functional import element_wise_apply
from msgspec import Struct, field
from msgspec.structs import astuple, replace


class Priority(enum.IntEnum):
    unvalued = 0
    prioritized = 1
    full_negative_only = 2
    half_negative_only = 4


class StatPriority(Struct, frozen=True):
    distance_mastery: Priority = Priority.unvalued
    rear_mastery: Priority = Priority.unvalued
    heal_mastery: Priority = Priority.unvalued
    beserk_mastery: Priority = Priority.unvalued
    melee_mastery: Priority = Priority.unvalued
    number_of_elements: int = 3


class Sublimation(Struct, frozen=True):
    sublimation_id: int
    level: int | None = None
    

class Stats(Struct, frozen=True, gc=True):
    ap: int = 0
    mp: int = 0
    wp: int = 0
    ra: int = 0
    crit: int = 0
    crit_mastery: int = 0
    elemental_mastery: int = 0
    one_element_mastery: int = 0
    two_element_mastery: int = 0
    three_element_mastery: int = 0
    distance_mastery: int = 0
    rear_mastery: int = 0
    heal_mastery: int = 0
    beserk_mastery: int = 0
    melee_mastery: int = 0
    control: int = 0
    block: int = 0
    fd: int = 0
    heals_performed: int = 0
    lock: int = 0
    dodge: int = 0

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

    def unhandled(self) -> bool:
        _ap, _mp, wp, _ra, _crit, *rest = astuple(self)
        return any(stat != DUMMY_MIN for stat in (wp, *rest))


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

    def unhandled(self) -> bool:
        _ap, _mp, wp, _ra, _crit, *rest = astuple(self)
        return any(stat != DUMMY_MAX for stat in (wp, *rest))


def effective_mastery(stats: Stats, rel_mastery_key: Callable[[Stats], int]) -> float:
    # there's a hidden 3% base crit rate in game
    # There's also clamping on crit rate
    crit_rate = max(min(stats.crit + 3, 100), 0)

    fd = 1 + (stats.fd / 100)

    rel_mastery = rel_mastery_key(stats)

    return (rel_mastery * (100 - crit_rate) / 100) * fd + ((rel_mastery + stats.crit_mastery) * crit_rate * (fd + 0.25))


def effective_healing(stats: Stats, rel_mastery_key: Callable[[Stats], int]) -> float:
    """
    We assume a worst case "heals didn't crit" for healing,
    under the philosophy of minimum healing required for safety.

    Crits under this philosophy *may* allow cutting a heal from a rotation on reaction
    making crit a damage stat even in the case of optimizing healing
    """
    return rel_mastery_key(stats) * (1 + (stats.heals_performed / 100))


def apply_w2h(stats: Stats) -> Stats:
    return replace(stats, ap=stats.ap + 2, mp=stats.mp - 2)


def apply_unravel(stats: Stats) -> Stats:
    if stats.crit >= 40:
        return replace(stats, elemental_mastery=stats.elemental_mastery + stats.crit_mastery, crit_mastery=0)
    return stats


def apply_elementalism(stats: Stats) -> Stats:
    if (stats.one_element_mastery == stats.two_element_mastery == 0) and stats.three_element_mastery != 0:
        return replace(stats, fd=stats.fd + 30, heals_performed=stats.heals_performed + 30)
    return stats


_DEFAULT_MIN_TUP: tuple[int, ...] = astuple(SetMinimums())
_DEFAULT_MAX_TUP: tuple[int, ...] = astuple(SetMaximums())


def generate_filter(
    base_stats: Stats,
    minimums: list[tuple[SetMinimums, ...]],
    maximums: list[tuple[SetMaximums, ...]],
) -> Callable[[list[Stats]], bool]:
    mins: list[tuple[int, ...]] = [astuple(i) for i in filter(None, chain.from_iterable(minimums))]
    maxs: list[tuple[int, ...]] = [astuple(i) for i in filter(None, chain.from_iterable(maximums))]

    if not (mins or maxs):
        return lambda _: True

    min_tup = element_wise_apply(max, mins) if mins else _DEFAULT_MIN_TUP
    max_tup = element_wise_apply(min, maxs) if maxs else _DEFAULT_MAX_TUP

    def f(item_set: list[Stats]) -> bool:
        stat_tup = astuple(reduce(operator.add, (base_stats, *item_set)))

        return all(mn <= s <= mx for mn, s, mx in zip(min_tup, stat_tup, max_tup, strict=True))

    return f


class SolveConfig(Struct, frozen=True):
    #: Base stats should also include from shards and unconditional gains in passives
    #: And sublimations, but should not include any stat transforms!!
    lv: int = 230
    base_stats: Stats = field(default_factory=Stats)
    #: Warning, the more stats you set minimums and maximums for the longer a solution will take!
    set_minimums: SetMinimums = field(default_factory=SetMinimums)
    set_maximums: SetMaximums = field(default_factory=SetMaximums)
    stat_priorities: StatPriority = field(default_factory=StatPriority)
    forced_item_ids: list[int] = field(default_factory=list)
    forbidden_item_ids: list[int] = field(default_factory=list)
    equipped_sublimations: list[Sublimation] = field(default_factory=list)
    assume_double_damage_only_shards_are_damage: bool = True
    #: When set to True, the search will be done exhaustively
    #: When set to False, the search will adaptively determine when to end
    #: Based on intenrally maintained criteria that attempt to balance
    #: going through enough of the competitive options to at least find a 
    #: highly competitive option
    exhaustive: bool = False
    skip_shields: bool = True  # speeds up searches
    dry_run: bool = False


class Result(Struct):
    items: list[int] | None = None
    stats: Stats | None = None
    errors: list[str] | None = None
    eser_errors: list[str] | None = None
    user_warnings: list[str] | None = None


class DryRunResult(Struct):
    items: list[int] | None = None
    stats: None = None
    errors: list[str] | None = None
    user_errors: list[str] | None = None
    user_warnings: list[str] | None = None
