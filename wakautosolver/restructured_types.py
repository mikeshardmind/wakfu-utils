"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
# intentional restructuring the problem space a bit from solver.py
# Goal of simplifying the problem of allowing complex conditions to be expressible and performant

from __future__ import annotations

import bz2
import contextvars
import enum
import pathlib
import struct
import sys
from collections.abc import Callable
from dataclasses import asdict, astuple, dataclass, field, replace
from functools import lru_cache
from itertools import starmap
from typing import Literal, NamedTuple, TypedDict, final

if "pyodide" in sys.modules:
    import asyncio

    import micropip  # type: ignore

    tsk = asyncio.create_task(micropip.install("lzma"))  # type: ignore


_locale: contextvars.ContextVar[Literal["en", "es", "pt", "fr"]] = contextvars.ContextVar(
    "_locale", default="en"
)


def get_locale() -> Literal["en", "es", "pt", "fr"]:
    return _locale.get()


def set_locale(lc: Literal["en", "es", "pt", "fr"]) -> None:
    _locale.set(lc)


class PosData(TypedDict):
    position: list[str]
    title: dict[str, str]


ITEM_TYPE_MAP: dict[int, PosData] = {
    101: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Hache", "en": "Axe", "es": "Hacha", "pt": "Machado"},
    },
    103: {
        "position": ["LEFT_HAND", "RIGHT_HAND"],
        "title": {"fr": "Anneau", "en": "Ring", "es": "Anillo", "pt": "Anel"},
    },
    108: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Baguette", "en": "Wand", "es": "Varita", "pt": "Varinha"},
    },
    110: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Ep\u00e9e", "en": "Sword", "es": "Espada", "pt": "Espada"},
    },
    111: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Pelle", "en": "Shovel", "es": "Pala", "pt": "P\u00e1"},
    },
    112: {
        "position": ["SECOND_WEAPON"],
        "title": {"fr": "Dague", "en": "Dagger", "es": "Daga", "pt": "Adaga"},
    },
    113: {
        "position": ["FIRST_WEAPON"],
        "title": {
            "fr": "B\u00e2ton",
            "en": "One-handed Staff",
            "es": "Bast\u00f3n",
            "pt": "Bast\u00e3o",
        },
    },
    114: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Marteau", "en": "Hammer", "es": "Martillo", "pt": "Martelo"},
    },
    115: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Aiguille", "en": "Hand", "es": "Aguja", "pt": "Ponteiro"},
    },
    117: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Arc", "en": "Bow", "es": "Arco", "pt": "Arco"},
    },
    119: {
        "position": ["LEGS"],
        "title": {"fr": "Bottes", "en": "Boots", "es": "Botas", "pt": "Botas"},
    },
    120: {
        "position": ["NECK"],
        "title": {"fr": "Amulette", "en": "Amulet", "es": "Amuleto", "pt": "Amuleto"},
    },
    132: {
        "position": ["BACK"],
        "title": {"fr": "Cape", "en": "Cloak", "es": "Capa", "pt": "Capa"},
    },
    133: {
        "position": ["BELT"],
        "title": {"fr": "Ceinture", "en": "Belt", "es": "Cintur\u00f3n", "pt": "Cinto"},
    },
    134: {
        "position": ["HEAD"],
        "title": {"fr": "Casque", "en": "Helmet", "es": "Casco", "pt": "Capacete"},
    },
    136: {
        "position": ["CHEST"],
        "title": {
            "fr": "Plastron",
            "en": "Breastplate",
            "es": "Coraza",
            "pt": "Peitoral",
        },
    },
    138: {
        "position": ["SHOULDERS"],
        "title": {
            "fr": "Epaulettes",
            "en": "Epaulettes",
            "es": "Hombreras",
            "pt": "Dragonas",
        },
    },
    189: {
        "position": ["SECOND_WEAPON"],
        "title": {"fr": "Bouclier", "en": "Shield", "es": "Escudo", "pt": "Escudo"},
    },
    219: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Poing", "en": "Fist", "es": "Pu\u00f1o", "pt": "Punho "},
    },
    223: {
        "position": ["FIRST_WEAPON"],
        "title": {
            "fr": "Ep\u00e9e \u00e0 2 mains",
            "en": "Two-handed Sword",
            "es": "Espada a dos manos",
            "pt": "Espada de 2 m\u00e3os",
        },
    },
    253: {
        "position": ["FIRST_WEAPON"],
        "title": {
            "fr": "B\u00e2ton \u00e0 2 mains",
            "en": "Two-handed Staff",
            "es": "Bast\u00f3n a dos manos",
            "pt": "Bast\u00e3o de 2 m\u00e3os",
        },
    },
    254: {
        "position": ["FIRST_WEAPON"],
        "title": {"fr": "Cartes", "en": "Cards", "es": "Cartas", "pt": "Cartas"},
    },
    480: {
        "position": ["ACCESSORY"],
        "title": {"fr": "Torches", "en": "Torches", "es": "Antorchas", "pt": "Tochas"},
    },
    518: {
        "position": ["FIRST_WEAPON"],
        "title": {
            "fr": "Armes 1 Main",
            "en": "One-Handed Weapons",
            "es": "Armas de una mano",
            "pt": "Armas de 1 m\u00e3o",
        },
    },
    519: {
        "position": ["FIRST_WEAPON"],
        "title": {
            "fr": "Armes 2 Mains",
            "en": "Two-Handed Weapons",
            "es": "Armas de dos manos",
            "pt": "Armas de 2 m\u00e3os",
        },
    },
    520: {
        "position": ["SECOND_WEAPON"],
        "title": {
            "fr": "Seconde Main",
            "en": "Second Hand",
            "es": "Segunda mano",
            "pt": "Segunda m\u00e3o",
        },
    },
    537: {
        "position": ["ACCESSORY"],
        "title": {
            "fr": "Outils",
            "en": "Tools",
            "es": "Herramientas",
            "pt": "Ferramentas",
        },
    },
    582: {
        "position": ["PET"],
        "title": {"fr": "Familiers", "en": "Pets", "es": "Mascotas", "pt": "Mascotes"},
    },
    611: {
        "position": ["MOUNT"],
        "title": {
            "fr": "Montures",
            "en": "Mounts",
            "es": "Monturas",
            "pt": "Montarias",
        },
    },
    646: {
        "position": ["ACCESSORY"],
        "title": {
            "fr": "Embl\u00e8me",
            "en": "Emblem",
            "es": "Emblema",
            "pt": "Emblema",
        },
    },
    647: {
        "position": ["COSTUME"],
        "title": {"fr": "Costumes", "en": "Costumes", "es": "Trajes", "pt": "Trajes"},
    },
}


@final
class EquipableItem(NamedTuple):
    item_id: int
    item_lv: int
    item_rarity: int
    item_type: int
    hp: int = 0
    ap: int = 0
    mp: int = 0
    wp: int = 0
    ra: int = 0
    control: int = 0
    block: int = 0
    critical_hit: int = 0
    dodge: int = 0
    lock: int = 0
    force_of_will: int = 0
    rear_mastery: int = 0
    healing_mastery: int = 0
    melee_mastery: int = 0
    distance_mastery: int = 0
    berserk_mastery: int = 0
    critical_mastery: int = 0
    fire_mastery: int = 0
    earth_mastery: int = 0
    water_mastery: int = 0
    air_mastery: int = 0
    mastery_1_element: int = 0
    mastery_2_elements: int = 0
    mastery_3_elements: int = 0
    elemental_mastery: int = 0
    resistance_1_element: int = 0
    resistance_2_elements: int = 0
    resistance_3_elements: int = 0
    fire_resistance: int = 0
    earth_resistance: int = 0
    water_resistance: int = 0
    air_resistance: int = 0
    elemental_resistance: int = 0
    rear_resistance: int = 0
    critical_resistance: int = 0
    armor_given: int = 0
    armor_received: int = 0

    @property
    def fd(self) -> float:
        return 0.0

    @property
    def heals_performed(self) -> int:
        return 0

    @property
    def total_elemental_res(self) -> int:
        """This is here for quick selection pre tuning"""
        return (
            +self.fire_resistance
            + self.air_resistance
            + self.water_resistance
            + self.earth_resistance
            + self.resistance_1_element
            + self.resistance_2_elements * 2
            + self.resistance_3_elements * 3
            + self.elemental_resistance * 4
        )

    def as_stats(self) -> Stats:
        return _item_to_stats(self)

    @property
    def num_random_mastery(self) -> int:
        if self.mastery_3_elements:
            return 3
        if self.mastery_2_elements:
            return 2
        if self.mastery_1_element:
            return 1
        return 0

    @property
    def is_relic(self) -> bool:
        return self.item_rarity == 5

    @property
    def is_souvenir(self) -> bool:
        return self.item_rarity == 6

    @property
    def is_epic(self) -> bool:
        return self.item_rarity == 7

    @property
    def item_slot(self) -> str:
        return ITEM_TYPE_MAP[self.item_type]["position"][0]

    @property
    def disables_second_weapon(self) -> bool:
        return self.item_type in {101, 111, 114, 117, 223, 253, 519}

    @property
    def name(self) -> str:
        return get_item_name(self)

    def __repr__(self) -> str:
        rarities = {
            1: "Common",
            2: "Uncommon",
            3: "Mythic",
            4: "Legendary",
            5: "Relic",
            6: "Souvenir",
            7: "Epic",
        }
        rarity = rarities.get(self.item_rarity, "???")
        typ = ITEM_TYPE_MAP[self.item_type]["title"][_locale.get()]
        return f"Item id: {self.item_id:>5} [{rarity:>10}] {typ:>20} Lv: {self.item_lv:>3} {self.name}"


@lru_cache(None)
def _item_to_stats(item: EquipableItem) -> Stats:
    return Stats(
        ap=item.ap,
        mp=item.mp,
        wp=item.wp,
        ra=item.ra,
        critical_hit=item.critical_hit,
        critical_mastery=item.critical_mastery,
        elemental_mastery=item.elemental_mastery,
        mastery_1_element=item.mastery_1_element,
        mastery_2_elements=item.mastery_2_elements,
        mastery_3_elements=item.mastery_3_elements,
        distance_mastery=item.distance_mastery,
        rear_mastery=item.rear_mastery,
        healing_mastery=item.healing_mastery,
        berserk_mastery=item.berserk_mastery,
        melee_mastery=item.melee_mastery,
        control=item.control,
        block=item.block,
        lock=item.lock,
        dodge=item.dodge,
        fd=0,
        heals_performed=0,
    )


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


class ElementsEnum(enum.IntFlag):
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
    ClassesEnum.Hupper: ElementsEnum.water
    | ElementsEnum.fire
    | ElementsEnum.earth
    | ElementsEnum.air,
}


class Priority(enum.IntEnum):
    unvalued = 0
    prioritized = 1
    full_negative_only = 2
    half_negative_only = 4


@dataclass
class StatPriority:
    distance_mastery: Priority = Priority.unvalued
    melee_mastery: Priority = Priority.unvalued
    heal_mastery: Priority = Priority.unvalued
    rear_mastery: Priority = Priority.unvalued
    berserk_mastery: Priority = Priority.unvalued
    elements: ElementsEnum = ElementsEnum.empty

    def _pyodide_norm(self) -> None:
        self.distance_mastery = Priority(self.distance_mastery)
        self.melee_mastery = Priority(self.melee_mastery)
        self.heal_mastery = Priority(self.heal_mastery)
        self.rear_mastery = Priority(self.rear_mastery)
        self.berserk_mastery = Priority(self.berserk_mastery)
        self.elements = ElementsEnum(self.elements)

    @property
    def is_valid(self) -> bool:
        return all(
            x < 2 for x in (self.distance_mastery, self.melee_mastery, self.heal_mastery)
        )


@dataclass(unsafe_hash=True)
class Stats:
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
    fd: float = 0
    heals_performed: int = 0
    lock: int = 0
    dodge: int = 0
    armor_given: int = 0

    def __sub__(self, other: Stats | EquipableItem) -> Stats:
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

    def __add__(self, other: Stats | EquipableItem) -> Stats:
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

    def __le__(self, other: Stats | SetMinimums | SetMaximums) -> bool:
        return all((
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
        ))


DUMMY_MIN: int = -1_000_000
DUMMY_MAX: int = 1_000_000

SIMMABLE = ["ap", "mp", "wp", "ra", "block", "armor_given"]


class SetMinimums(Stats):
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
    fd: float = DUMMY_MIN
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

    def __and__(self, other: SetMinimums) -> SetMinimums:
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

    def __le__(self, other: Stats | SetMinimums | SetMaximums) -> bool:
        return all((
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
        ))


class SetMaximums(Stats):
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
    fd: float = DUMMY_MAX
    heals_performed: int = DUMMY_MAX
    lock: int = DUMMY_MAX
    dodge: int = DUMMY_MAX
    armor_given: int = DUMMY_MAX

    def unhandled(self) -> bool:
        _ap, _mp, _wp, _ra, _crit, *rest = astuple(self)
        return any(stat != DUMMY_MAX for stat in rest)

    def __and__(self, other: SetMaximums) -> SetMaximums:
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

    return (rel_mastery * (100 - crit_rate) / 100) * fd + (
        (rel_mastery + stats.critical_mastery) * crit_rate * (fd + 0.25)
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
    return replace(stats, ap=stats.ap + 2, mp=stats.mp - 2)


def apply_unravel(stats: Stats) -> Stats:
    if stats.critical_hit >= 40:
        return replace(
            stats,
            elemental_mastery=stats.elemental_mastery + stats.critical_mastery,
            crit_mastery=0,
        )
    return stats


def apply_elementalism(stats: Stats) -> Stats:
    if (
        stats.mastery_1_element == stats.mastery_2_elements == 0
    ) and stats.mastery_3_elements != 0:
        return replace(
            stats, fd=stats.fd + 30, heals_performed=stats.heals_performed + 30
        )
    return stats


@dataclass
class v1Config:
    lv: int = 230
    ap: int = 5
    mp: int = 2
    wp: int = 0
    ra: int = 0
    wakfu_class: ClassesEnum = ClassesEnum.EMPTY
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


class LocaleData(NamedTuple):
    en: str = ""
    es: str = ""
    fr: str = ""
    pt: str = ""


class SourceData(NamedTuple):
    arch: frozenset[int]
    horde: frozenset[int]
    non_finite_arch_horde: frozenset[int]
    pvp: frozenset[int]
    ultimate_boss: frozenset[int]
    legacy_items: frozenset[int]
    blueprints: frozenset[int]


LocaleBundle = dict[int, LocaleData]
StatOnlyBundle = tuple[EquipableItem, ...]


def get_item_name(item: EquipableItem) -> str:
    if item.item_id == -2:
        return "LIGHT WEAPON EXPERT PLACEHOLDER"
    i = load_locale_data().get(item.item_id, LocaleData())
    return getattr(i, _locale.get())


def unpack_items(packed: bytes) -> list[EquipableItem]:
    return list(starmap(EquipableItem, struct.iter_unpack("!IHBH37h", packed)))


@lru_cache
def get_all_items() -> StatOnlyBundle:
    import lzma

    data_file_path = pathlib.Path(__file__).with_name("data") / "stat_only_bundle.xz"
    with lzma.open(data_file_path, format=lzma.FORMAT_XZ) as fp:
        return tuple(unpack_items(fp.read()))


def unpack_locale_data(packed: bytes) -> LocaleBundle:
    ret: LocaleBundle = {}
    offset = 0
    while offset < len(packed):
        (item_id,) = struct.unpack_from("!I", packed, offset)
        offset += struct.calcsize("!I")

        strs: list[str] = []
        for _ in range(4):
            (s_len,) = struct.unpack_from("!B", packed, offset)
            offset += struct.calcsize("!B")
            fmt = "!%ds" % s_len
            (s,) = struct.unpack_from(fmt, packed, offset)
            offset += struct.calcsize(fmt)
            strs.append(s.decode("utf-8"))

        ret[item_id] = LocaleData(*strs)

    return ret


@lru_cache
def load_locale_data() -> LocaleBundle:
    data_file_path = pathlib.Path(__file__).with_name("data") / "locale_bundle.bz2"
    with bz2.open(data_file_path, mode="rb", compresslevel=9) as fp:
        return unpack_locale_data(fp.read())


def unpack_sourcedata(packed: bytes) -> SourceData:
    offset = 0
    sets: list[frozenset[int]] = []
    while offset < len(packed):
        (ilen,) = struct.unpack_from("!I", packed, offset)
        offset += struct.calcsize("!I")
        fmt = "!%dI" % ilen
        items = frozenset(struct.unpack_from(fmt, packed, offset))
        sets.append(items)
        offset += struct.calcsize(fmt)

    return SourceData(*sets)


@lru_cache
def load_item_source_data() -> SourceData:
    data_file_path = pathlib.Path(__file__).with_name("data") / "source_info.xz"
    import lzma

    with lzma.open(data_file_path, format=lzma.FORMAT_XZ) as fp:
        return unpack_sourcedata(fp.read())
