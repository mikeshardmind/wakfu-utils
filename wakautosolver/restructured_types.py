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
from collections.abc import Callable
from typing import Literal

from msgspec import Struct, field
from msgspec.structs import asdict, astuple, replace


class ClassesEnum(enum.IntEnum):
    EMPTY = -1
    Feca = 0
    Osa = 1
    Osamodas = Osa
    Enu = 2
    Enutrof = Enu
    Sram = 3
    Xel = 4
    Xelor = Xel
    Eca = 5
    Ecaflip = Eca
    Eni = 6
    Eniripsa = Eni
    Iop = 7
    Cra = 8
    Sadi = 9
    Sadida = Sadi
    Sac = 10
    Sacrier = Sac
    Panda = 11
    Pandawa = Panda
    Rogue = 12
    Masq = 13
    Masqueraiders = Masq
    Ougi = 14
    Ouginak = Ougi
    Fog = 15
    Foggernaut = Fog
    Elio = 16
    Eliotrope = Elio
    Hupper = 17
    Huppermage = Hupper


class ElementsEnum(enum.IntFlag, boundary=enum.STRICT):
    empty = 0
    fire = 1 << 0
    earth = 1 << 1
    water = 1 << 2
    air = 1 << 3


ClassElements: dict[ClassesEnum, ElementsEnum] = {
    ClassesEnum.EMPTY: ElementsEnum.empty,
    ClassesEnum.Feca: ElementsEnum.earth | ElementsEnum.fire | ElementsEnum.water,
    ClassesEnum.Osa: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Enu: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.water,
    ClassesEnum.Sram: ElementsEnum.fire | ElementsEnum.water | ElementsEnum.air,
    ClassesEnum.Xel: ElementsEnum.fire | ElementsEnum.water | ElementsEnum.air,
    ClassesEnum.Eca: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.water,
    ClassesEnum.Eni: ElementsEnum.fire | ElementsEnum.water | ElementsEnum.air,
    ClassesEnum.Iop: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Cra: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Sadi: ElementsEnum.water | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Sac: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Panda: ElementsEnum.earth | ElementsEnum.fire | ElementsEnum.water,
    ClassesEnum.Rogue: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Masq: ElementsEnum.fire | ElementsEnum.water | ElementsEnum.air,
    ClassesEnum.Ougi: ElementsEnum.water | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Fog: ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.water,
    ClassesEnum.Elio: ElementsEnum.water | ElementsEnum.earth | ElementsEnum.air,
    ClassesEnum.Hupper: ElementsEnum.water | ElementsEnum.fire | ElementsEnum.earth | ElementsEnum.air,
}


class Priority(enum.IntEnum):
    unvalued = 0
    prioritized = 1
    full_negative_only = 2
    half_negative_only = 4


class StatPriority(Struct, frozen=True, array_like=True):
    distance_mastery: Priority = Priority.unvalued
    melee_mastery: Priority = Priority.unvalued
    heal_mastery: Priority = Priority.unvalued
    rear_mastery: Priority = Priority.unvalued
    berserk_mastery: Priority = Priority.unvalued
    elements: ElementsEnum = ElementsEnum.empty

    @property
    def is_valid(self) -> bool:
        return all(x < 2 for x in (self.distance_mastery, self.melee_mastery, self.heal_mastery))


class Stats(Struct, frozen=True, gc=True):
    ap: int = 0
    mp: int = 0
    wp: int = 0
    ra: int = 0
    critical_hit: int = 0
    critical_mastery: int = 0
    elemental_mastery: int = 0
    mastery_3_elements: int = 0
    mastery_2_elements: int = 0
    mastery_1_element: int = 0
    distance_mastery: int = 0
    rear_mastery: int = 0
    healing_mastery: int = 0
    berserk_mastery: int = 0
    melee_mastery: int = 0
    control: int = 0
    block: int = 0
    fd: int = 0
    heals_performed: int = 0
    lock: int = 0
    dodge: int = 0
    armor_given: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stats):
            return NotImplemented
        return astuple(self) == astuple(other)

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Stats):
            return NotImplemented
        return astuple(self) != astuple(other)

    def __sub__(self, other: object) -> Stats:
        if not isinstance(other, Stats):
            return NotImplemented

        return Stats(
            self.ap - other.ap,
            self.mp - other.mp,
            self.wp - other.wp,
            self.ra - other.ra,
            self.critical_hit - other.critical_hit,
            self.critical_mastery - other.critical_mastery,
            self.elemental_mastery - other.elemental_mastery,
            self.mastery_3_elements - other.mastery_3_elements,
            self.mastery_2_elements - other.mastery_2_elements,
            self.mastery_1_element - other.mastery_1_element,
            self.distance_mastery - other.distance_mastery,
            self.rear_mastery - other.rear_mastery,
            self.healing_mastery - other.healing_mastery,
            self.berserk_mastery - other.berserk_mastery,
            self.melee_mastery - other.melee_mastery,
            self.control - other.control,
            self.block - other.block,
            self.fd - other.fd,
            self.heals_performed - other.heals_performed,
            self.lock - other.lock,
            self.dodge - other.dodge,
            self.armor_given - other.armor_given,
        )

    def __add__(self, other: object) -> Stats:
        if not isinstance(other, Stats):
            return NotImplemented

        return Stats(
            self.ap + other.ap,
            self.mp + other.mp,
            self.wp + other.wp,
            self.ra + other.ra,
            self.critical_hit + other.critical_hit,
            self.critical_mastery + other.critical_mastery,
            self.elemental_mastery + other.elemental_mastery,
            self.mastery_3_elements + other.mastery_3_elements,
            self.mastery_2_elements + other.mastery_2_elements,
            self.mastery_1_element + other.mastery_1_element,
            self.distance_mastery + other.distance_mastery,
            self.rear_mastery + other.rear_mastery,
            self.healing_mastery + other.healing_mastery,
            self.berserk_mastery + other.berserk_mastery,
            self.melee_mastery + other.melee_mastery,
            self.control + other.control,
            self.block + other.block,
            self.fd + other.fd,
            self.heals_performed + other.heals_performed,
            self.lock + other.lock,
            self.dodge + other.dodge,
            self.armor_given + other.armor_given,
        )

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Stats):
            return NotImplemented

        return all(
            (
                self.ap <= other.ap,
                self.mp <= other.mp,
                self.wp <= other.wp,
                self.ra <= other.ra,
                self.critical_hit <= other.critical_hit,
                self.critical_mastery <= other.critical_mastery,
                self.elemental_mastery <= other.elemental_mastery,
                self.mastery_3_elements <= other.mastery_3_elements,
                self.mastery_2_elements <= other.mastery_2_elements,
                self.mastery_1_element <= other.mastery_1_element,
                self.distance_mastery <= other.distance_mastery,
                self.rear_mastery <= other.rear_mastery,
                self.healing_mastery <= other.healing_mastery,
                self.berserk_mastery <= other.berserk_mastery,
                self.melee_mastery <= other.melee_mastery,
                self.control <= other.control,
                self.block <= other.block,
                self.fd <= other.fd,
                self.heals_performed <= other.heals_performed,
                self.lock <= other.lock,
                self.dodge <= other.dodge,
                self.armor_given <= other.armor_given,
            )
        )


DUMMY_MIN: int = -1_000_000
DUMMY_MAX: int = 1_000_000

SIMMABLE = ["ap", "mp", "wp", "ra", "block", "armor_given"]


class SetMinimums(Stats, frozen=True, gc=False):
    ap: int = DUMMY_MIN
    mp: int = DUMMY_MIN
    wp: int = DUMMY_MIN
    ra: int = DUMMY_MIN
    critical_hit: int = DUMMY_MIN
    critical_mastery: int = DUMMY_MIN
    elemental_mastery: int = DUMMY_MIN
    mastery_3_elements: int = DUMMY_MIN
    mastery_2_elements: int = DUMMY_MIN
    mastery_1_element: int = DUMMY_MIN
    distance_mastery: int = DUMMY_MIN
    rear_mastery: int = DUMMY_MIN
    healing_mastery: int = DUMMY_MIN
    berserk_mastery: int = DUMMY_MIN
    melee_mastery: int = DUMMY_MIN
    control: int = DUMMY_MIN
    block: int = DUMMY_MIN
    fd: int = DUMMY_MIN
    heals_performed: int = DUMMY_MIN
    lock: int = DUMMY_MIN
    dodge: int = DUMMY_MIN
    armor_given: int = DUMMY_MIN

    def stats_met(self, other: Stats) -> bool:
        return not any(o < s for s, o in zip(astuple(self), astuple(other), strict=True))

    def get_sim_keys(self) -> list[str]:
        return [k for k, v in asdict(self).items() if v != DUMMY_MIN and k in SIMMABLE]

    def unhandled(self) -> bool:
        _ap, _mp, _wp, _ra, _crit, *rest = astuple(self)
        return any(stat != DUMMY_MIN for stat in rest)

    def __and__(self, other: object) -> SetMinimums:
        if not isinstance(other, SetMinimums):
            return NotImplemented

        return SetMinimums(
            max(self.ap, other.ap),
            max(self.mp, other.mp),
            max(self.wp, other.wp),
            max(self.ra, other.ra),
            max(self.critical_hit, other.critical_hit),
            max(self.critical_mastery, other.critical_mastery),
            max(self.elemental_mastery, other.elemental_mastery),
            max(self.mastery_3_elements, other.mastery_3_elements),
            max(self.mastery_2_elements, other.mastery_2_elements),
            max(self.mastery_1_element, other.mastery_1_element),
            max(self.distance_mastery, other.distance_mastery),
            max(self.rear_mastery, other.rear_mastery),
            max(self.healing_mastery, other.healing_mastery),
            max(self.berserk_mastery, other.berserk_mastery),
            max(self.melee_mastery, other.melee_mastery),
            max(self.control, other.control),
            max(self.block, other.block),
            max(self.fd, other.fd),
            max(self.heals_performed, other.heals_performed),
            max(self.lock, other.lock),
            max(self.dodge, other.dodge),
            max(self.armor_given, other.armor_given),
        )

    def __le__(self, other: object):
        if not isinstance(other, Stats):
            return NotImplemented

        return all(
            (
                self.ap <= other.ap,
                self.mp <= other.mp,
                self.wp <= other.wp,
                self.ra <= other.ra,
                self.critical_hit <= other.critical_hit,
                self.critical_mastery <= other.critical_mastery,
                self.elemental_mastery <= other.elemental_mastery,
                self.mastery_3_elements <= other.mastery_3_elements,
                self.mastery_2_elements <= other.mastery_2_elements,
                self.mastery_1_element <= other.mastery_1_element,
                self.distance_mastery <= other.distance_mastery,
                self.rear_mastery <= other.rear_mastery,
                self.healing_mastery <= other.healing_mastery,
                self.berserk_mastery <= other.berserk_mastery,
                self.melee_mastery <= other.melee_mastery,
                self.control <= other.control,
                self.block <= other.block,
                self.fd <= other.fd,
                self.heals_performed <= other.heals_performed,
                self.lock <= other.lock,
                self.dodge <= other.dodge,
                self.armor_given <= other.armor_given,
            )
        )


class SetMaximums(Stats, frozen=True, gc=False):
    ap: int = DUMMY_MAX
    mp: int = DUMMY_MAX
    wp: int = DUMMY_MAX
    ra: int = DUMMY_MAX
    critical_hit: int = DUMMY_MAX
    critical_mastery: int = DUMMY_MAX
    elemental_mastery: int = DUMMY_MAX
    mastery_3_elements: int = DUMMY_MAX
    mastery_2_elements: int = DUMMY_MAX
    mastery_1_element: int = DUMMY_MAX
    distance_mastery: int = DUMMY_MAX
    rear_mastery: int = DUMMY_MAX
    healing_mastery: int = DUMMY_MAX
    berserk_mastery: int = DUMMY_MAX
    melee_mastery: int = DUMMY_MAX
    control: int = DUMMY_MAX
    block: int = DUMMY_MAX
    fd: int = DUMMY_MAX
    heals_performed: int = DUMMY_MAX
    lock: int = DUMMY_MAX
    dodge: int = DUMMY_MAX
    armor_given: int = DUMMY_MAX

    def unhandled(self) -> bool:
        _ap, _mp, _wp, _ra, _crit, *rest = astuple(self)
        return any(stat != DUMMY_MAX for stat in rest)

    def __and__(self, other: object) -> SetMaximums:
        if not isinstance(other, SetMaximums):
            return NotImplemented

        return SetMaximums(
            min(self.ap, other.ap),
            min(self.mp, other.mp),
            min(self.wp, other.wp),
            min(self.ra, other.ra),
            min(self.critical_hit, other.critical_hit),
            min(self.critical_mastery, other.critical_mastery),
            min(self.elemental_mastery, other.elemental_mastery),
            min(self.mastery_3_elements, other.mastery_3_elements),
            min(self.mastery_2_elements, other.mastery_2_elements),
            min(self.mastery_1_element, other.mastery_1_element),
            min(self.distance_mastery, other.distance_mastery),
            min(self.rear_mastery, other.rear_mastery),
            min(self.healing_mastery, other.healing_mastery),
            min(self.berserk_mastery, other.berserk_mastery),
            min(self.melee_mastery, other.melee_mastery),
            min(self.control, other.control),
            min(self.block, other.block),
            min(self.fd, other.fd),
            min(self.heals_performed, other.heals_performed),
            min(self.lock, other.lock),
            min(self.dodge, other.dodge),
            min(self.armor_given, other.armor_given),
        )


def effective_mastery(stats: Stats, rel_mastery_key: Callable[[Stats], int]) -> float:
    # there's a hidden 3% base crit rate in game
    # There's also clamping on crit rate
    crit_rate = max(min(stats.critical_hit + 3, 100), 0)

    fd = 1 + (stats.fd / 100)

    rel_mastery = rel_mastery_key(stats)

    return (rel_mastery * (100 - crit_rate) / 100) * fd + ((rel_mastery + stats.critical_mastery) * crit_rate * (fd + 0.25))


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
    if stats.critical_hit >= 40:
        return replace(stats, elemental_mastery=stats.elemental_mastery + stats.critical_mastery, crit_mastery=0)
    return stats


def apply_elementalism(stats: Stats) -> Stats:
    if (stats.mastery_1_element == stats.mastery_2_elements == 0) and stats.mastery_3_elements != 0:
        return replace(stats, fd=stats.fd + 30, heals_performed=stats.heals_performed + 30)
    return stats


class v1Config(Struct, kw_only=True):
    lv: int = 230
    ap: int = 5
    mp: int = 2
    wp: int = 0
    ra: int = 0
    base_stats: Stats | None = None
    stat_minimums: SetMinimums | None = None
    stat_maximums: SetMaximums | None = None
    num_mastery: int = 3
    dist: bool = False
    melee: bool = False
    zerk: bool = False
    rear: bool = False
    heal: bool = False
    unraveling: bool = False
    skipshields: bool = False
    lwx: bool = False
    bcrit: int = 0
    bmast: int = 0
    bcmast: int = 0
    forbid: list[str] = field(default_factory=list)
    idforbid: list[int] = field(default_factory=list)
    idforce: list[int] = field(default_factory=list)
    twoh: bool = False
    skiptwo_hand: bool = False
    locale: Literal["en", "fr", "pt", "es"] = "en"
    dry_run: bool = False
    hard_cap_depth: int = 25
    negzerk: Literal["full", "half", "none"] = "none"
    negrear: Literal["full", "half", "none"] = "none"
    forbid_rarity: list[int] = field(default_factory=list)
    allowed_rarities: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    nameforce: list[str] = field(default_factory=list)
    tolerance: int = 30
    # Don't modify the below in wakforge, too slow
    exhaustive: bool = False
    search_depth: int = 1
    # dont touch these in wakforge either
    baseap: int = 0
    basemp: int = 0
    bawewp: int = 0
    basera: int = 0
    elements: ElementsEnum = ElementsEnum.empty
