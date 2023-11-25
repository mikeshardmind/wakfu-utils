"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import bz2
import contextvars
import pathlib
from functools import lru_cache
from typing import Literal, TypedDict

from msgspec import Struct, msgpack

from .restructured_types import Stats

_locale: contextvars.ContextVar[Literal["en", "es", "pt", "fr"]] = contextvars.ContextVar("_locale", default="en")


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


class EquipableItem(Struct, frozen=True, array_like=True):
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
        return self.item_type in (101, 111, 114, 117, 223, 253, 519)

    @property
    def name(self) -> str:
        return _get_item_name(self)

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


@lru_cache
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


class LocaleData(Struct, frozen=True, array_like=True):
    en: str = ""
    es: str = ""
    fr: str = ""
    pt: str = ""

    def __getitem__(self, key: str, /) -> str:
        return getattr(self, key, "")


class SourceData(Struct, frozen=True, array_like=True):
    arch: frozenset[int]
    horde: frozenset[int]
    non_finite_arch_horde: frozenset[int]
    pvp: frozenset[int]
    ultimate_boss: frozenset[int]


LocaleBundle = dict[int, LocaleData]
StatOnlyBundle = tuple[EquipableItem, ...]


def _get_item_name(item: EquipableItem) -> str:
    if item.item_id == -2:
        return "LIGHT WEAPON EXPERT PLACEHOLDER"
    return load_locale_data().get(item.item_id, LocaleData())[get_locale()]


@lru_cache
def get_all_items() -> StatOnlyBundle:
    data_file_path = pathlib.Path(__file__).with_name("data") / "stat_only_bundle.bz2"
    with bz2.open(data_file_path, mode="rb", compresslevel=9) as fp:
        return msgpack.decode(fp.read(), type=StatOnlyBundle)


@lru_cache
def load_locale_data() -> LocaleBundle:
    data_file_path = pathlib.Path(__file__).with_name("data") / "locale_bundle.bz2"
    with bz2.open(data_file_path, mode="rb", compresslevel=9) as fp:
        return msgpack.decode(fp.read(), type=LocaleBundle)


@lru_cache
def load_item_source_data() -> SourceData:
    data_file_path = pathlib.Path(__file__).with_name("data") / "source_info.bz2"
    with bz2.open(data_file_path, mode="rb", compresslevel=9) as fp:
        return msgpack.decode(fp.read(), type=SourceData)
