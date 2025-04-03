"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

# pyright: reportPrivateUsage=false
# pyright: reportConstantRedefinition=false
import bz2
import contextvars
import json
import logging
import pathlib
from collections.abc import Callable
from functools import cached_property
from typing import Any, Literal, Self, TypedDict


class PosData(TypedDict):
    position: list[str]
    disables: list[str]
    title: dict[str, str]


ITEM_TYPE_MAP: dict[int, PosData] = {
    101: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {"fr": "Hache", "en": "Axe", "es": "Hacha", "pt": "Machado"},
    },
    103: {
        "position": ["LEFT_HAND", "RIGHT_HAND"],
        "disables": [],
        "title": {"fr": "Anneau", "en": "Ring", "es": "Anillo", "pt": "Anel"},
    },
    108: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {"fr": "Baguette", "en": "Wand", "es": "Varita", "pt": "Varinha"},
    },
    110: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {"fr": "Ep\u00e9e", "en": "Sword", "es": "Espada", "pt": "Espada"},
    },
    111: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {"fr": "Pelle", "en": "Shovel", "es": "Pala", "pt": "P\u00e1"},
    },
    112: {
        "position": ["SECOND_WEAPON"],
        "disables": [],
        "title": {"fr": "Dague", "en": "Dagger", "es": "Daga", "pt": "Adaga"},
    },
    113: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {
            "fr": "B\u00e2ton",
            "en": "One-handed Staff",
            "es": "Bast\u00f3n",
            "pt": "Bast\u00e3o",
        },
    },
    114: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {"fr": "Marteau", "en": "Hammer", "es": "Martillo", "pt": "Martelo"},
    },
    115: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {"fr": "Aiguille", "en": "Hand", "es": "Aguja", "pt": "Ponteiro"},
    },
    117: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {"fr": "Arc", "en": "Bow", "es": "Arco", "pt": "Arco"},
    },
    119: {
        "position": ["LEGS"],
        "disables": [],
        "title": {"fr": "Bottes", "en": "Boots", "es": "Botas", "pt": "Botas"},
    },
    120: {
        "position": ["NECK"],
        "disables": [],
        "title": {"fr": "Amulette", "en": "Amulet", "es": "Amuleto", "pt": "Amuleto"},
    },
    132: {
        "position": ["BACK"],
        "disables": [],
        "title": {"fr": "Cape", "en": "Cloak", "es": "Capa", "pt": "Capa"},
    },
    133: {
        "position": ["BELT"],
        "disables": [],
        "title": {"fr": "Ceinture", "en": "Belt", "es": "Cintur\u00f3n", "pt": "Cinto"},
    },
    134: {
        "position": ["HEAD"],
        "disables": [],
        "title": {"fr": "Casque", "en": "Helmet", "es": "Casco", "pt": "Capacete"},
    },
    136: {
        "position": ["CHEST"],
        "disables": [],
        "title": {
            "fr": "Plastron",
            "en": "Breastplate",
            "es": "Coraza",
            "pt": "Peitoral",
        },
    },
    138: {
        "position": ["SHOULDERS"],
        "disables": [],
        "title": {
            "fr": "Epaulettes",
            "en": "Epaulettes",
            "es": "Hombreras",
            "pt": "Dragonas",
        },
    },
    189: {
        "position": ["SECOND_WEAPON"],
        "disables": [],
        "title": {"fr": "Bouclier", "en": "Shield", "es": "Escudo", "pt": "Escudo"},
    },
    219: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {"fr": "Poing", "en": "Fist", "es": "Pu\u00f1o", "pt": "Punho "},
    },
    223: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {
            "fr": "Ep\u00e9e \u00e0 2 mains",
            "en": "Two-handed Sword",
            "es": "Espada a dos manos",
            "pt": "Espada de 2 m\u00e3os",
        },
    },
    253: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {
            "fr": "B\u00e2ton \u00e0 2 mains",
            "en": "Two-handed Staff",
            "es": "Bast\u00f3n a dos manos",
            "pt": "Bast\u00e3o de 2 m\u00e3os",
        },
    },
    254: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {"fr": "Cartes", "en": "Cards", "es": "Cartas", "pt": "Cartas"},
    },
    480: {
        "position": ["ACCESSORY"],
        "disables": [],
        "title": {"fr": "Torches", "en": "Torches", "es": "Antorchas", "pt": "Tochas"},
    },
    518: {
        "position": ["FIRST_WEAPON"],
        "disables": [],
        "title": {
            "fr": "Armes 1 Main",
            "en": "One-Handed Weapons",
            "es": "Armas de una mano",
            "pt": "Armas de 1 m\u00e3o",
        },
    },
    519: {
        "position": ["FIRST_WEAPON"],
        "disables": ["SECOND_WEAPON"],
        "title": {
            "fr": "Armes 2 Mains",
            "en": "Two-Handed Weapons",
            "es": "Armas de dos manos",
            "pt": "Armas de 2 m\u00e3os",
        },
    },
    520: {
        "position": ["SECOND_WEAPON"],
        "disables": [],
        "title": {
            "fr": "Seconde Main",
            "en": "Second Hand",
            "es": "Segunda mano",
            "pt": "Segunda m\u00e3o",
        },
    },
    537: {
        "position": ["ACCESSORY"],
        "disables": [],
        "title": {
            "fr": "Outils",
            "en": "Tools",
            "es": "Herramientas",
            "pt": "Ferramentas",
        },
    },
    582: {
        "position": ["PET"],
        "disables": [],
        "title": {"fr": "Familiers", "en": "Pets", "es": "Mascotas", "pt": "Mascotes"},
    },
    611: {
        "position": ["MOUNT"],
        "disables": [],
        "title": {
            "fr": "Montures",
            "en": "Mounts",
            "es": "Monturas",
            "pt": "Montarias",
        },
    },
    646: {
        "position": ["ACCESSORY"],
        "disables": [],
        "title": {
            "fr": "Embl\u00e8me",
            "en": "Emblem",
            "es": "Emblema",
            "pt": "Emblema",
        },
    },
    647: {
        "position": ["COSTUME"],
        "disables": [],
        "title": {"fr": "Costumes", "en": "Costumes", "es": "Trajes", "pt": "Trajes"},
    },
}


_locale: contextvars.ContextVar[Literal["en", "es", "pt", "fr"]] = contextvars.ContextVar(
    "_locale", default="en"
)


_T39_EFFECT_LOOKUP: dict[int, str] = {
    121: "_armor_received",
    120: "_armor_given",
}

_T1068_EFFECT_LOOKUP: dict[int, str] = {
    1: "_mastery_1_element",
    2: "_mastery_2_elements",
    3: "_mastery_3_elements",
}

_T1069_EFFECT_LOOKUP: dict[int, str] = {
    1: "_resistance_1_element",
    2: "_resistance_2_elements",
    3: "_resistance_3_elements",
}


def type39(d: list[int]) -> list[tuple[str, int]]:
    """
    At current time, this is only used for armor recieved/armor given
    for the 215 tier content.
    I suspect more "special" item stats would appear here in the future.
    """
    key = d[4]
    val = d[0]

    try:
        return [(_T39_EFFECT_LOOKUP[key], val)]
    except KeyError:
        logging.warning("Got unhandled effect type. actionId 39 (%s)", key)
        return []


def type40(d: list[int]) -> list[tuple[str, int]]:
    """
    At current time, this is only used for armor recieved/armor given
    for the 215 tier content.
    I suspect more "special" item stats would appear here in the future.
    """
    key = d[4]
    val = d[0]

    try:
        return [(_T39_EFFECT_LOOKUP[key], 0 - val)]
    except KeyError:
        logging.warning("Got unhandled effect type. actionId 39 (%s)", key)
        return []


def type1068(d: list[int]) -> list[tuple[str, int]]:
    """
    This is used for specific element damage at current time
    """
    key = d[2]
    val = d[0]

    try:
        return [(_T1068_EFFECT_LOOKUP[key], val)]
    except KeyError:
        logging.warning("got unhandled effect type. actionId 1068 (%s)", key)
        return []


def type1069(d: list[int]) -> list[tuple[str, int]]:
    """
    This is used for specific element resistnace at current time
    """
    val = d[0]
    key = d[2]

    try:
        return [(_T1069_EFFECT_LOOKUP[key], val)]
    except KeyError:
        logging.warning("got unhandled effect type. actionId 1069 (%s)", key)
        return []


# This has been manually defined from the provided action data.
# Last updated at wakfu version "1.68.0.179615"
# Section should not be changed without updating last update.
# Accessing this map and not matching a value should be warned.

# Note: there are seperate effects for gaining and losing stat.
# At first I thought this might make sense with i18n phrasing,
# but it appears that there are not any cases in the data where this is true.
# I guess there could be in theory that havent materialized.
# It would prevent a needed migration if a language was added
# where the plain represetnation here isn't supported.
_EFFECT_MAP: dict[int, Callable[[list[int]], list[tuple[str, int]]]] = {
    20: lambda d: [("_hp", d[0])],
    21: lambda d: [("_hp", 0 - d[0])],
    26: lambda d: [("_healing_mastery", d[0])],
    31: lambda d: [("_ap", d[0])],
    32: lambda d: [("_ap", 0 - d[0])],  # old
    39: type39,  # requires a bit more logic
    40: type40,  # *sigh* same as above, but negatives
    41: lambda d: [("_mp", d[0])],
    42: lambda d: [("_mp", 0 - d[0])],  # old
    56: lambda d: [("_ap", 0 - d[0])],
    57: lambda d: [("_mp", 0 - d[0])],
    71: lambda d: [("_rear_resistance", d[0])],
    80: lambda d: [("_elemental_resistance", d[0])],
    82: lambda d: [("_fire_resistance", d[0])],
    83: lambda d: [("_water_resistance", d[0])],
    84: lambda d: [("_earth_resistance", d[0])],
    85: lambda d: [("_air_resistance", d[0])],
    # Below losses for res (next 4) are without cap
    # ex: 'Perte : Résistance Feu (sans cap)',
    # indicates capped resistance loss isn't generalized?
    96: lambda d: [("_earth_resistance", 0 - d[0])],
    97: lambda d: [("_fire_resistance", 0 - d[0])],
    98: lambda d: [("_water_resistance", 0 - d[0])],
    # Note, lack of air, reserved 99 for that?
    90: lambda d: [("_elemental_resistance", 0 - d[0])],
    100: lambda d: [("_elemental_resistance", 0 - d[0])],
    120: lambda d: [("_elemental_mastery", d[0])],
    122: lambda d: [("_fire_mastery", d[0])],
    123: lambda d: [("_earth_mastery", d[0])],
    124: lambda d: [("_water_mastery", d[0])],
    125: lambda d: [("_air_mastery", d[0])],
    130: lambda d: [("_elemental_mastery", 0 - d[0])],
    132: lambda d: [("_fire_mastery", 0 - d[0])],
    149: lambda d: [("_critical_mastery", d[0])],
    150: lambda d: [("_critical_hit", d[0])],
    160: lambda d: [("_ra", d[0])],
    161: lambda d: [("_ra", 0 - d[0])],
    162: lambda d: [("_prospecting", d[0])],
    166: lambda d: [("_wisdom", d[0])],
    # apparently the devs *are* cruel enough for -wis gear to exist
    # (see item # 11673, lv 65 skullenbone bat)
    167: lambda d: [("_wisdom", 0 - d[0])],
    168: lambda d: [("_critical_hit", 0 - d[0])],
    171: lambda d: [("_initiative", d[0])],
    172: lambda d: [("_initiative", 0 - d[0])],
    173: lambda d: [("_lock", d[0])],
    174: lambda d: [("_lock", 0 - d[0])],
    175: lambda d: [("_dodge", d[0])],
    176: lambda d: [("_dodge", 0 - d[0])],
    177: lambda d: [("_force_of_will", d[0])],
    180: lambda d: [("_rear_mastery", d[0])],
    181: lambda d: [("_rear_mastery", 0 - d[0])],
    184: lambda d: [("_control", d[0])],
    191: lambda d: [("_wp", d[0])],
    192: lambda d: [("_wp", 0 - d[0])],
    # 194 intetionally omitted, no items
    # It's a wp loss that no item appears to have in it's effects,
    # while 192 is a wp loss which is used
    # It will warn when an item is added where this needs handling at least.
    234: lambda d: [("_kit_skill", d[0])],
    # 304: Makabraktion ring's AP gain effect, intentionally unconsidered.
    304: lambda d: [],
    # 330 intetionally omitted, no items
    # 400: Aura effects? Not stats. It's mostly relics that have these,
    # along with the emblem lanterns (fire of darkness, jacko, etc)
    # but also mounts??)
    400: lambda d: [],
    832: lambda d: [],  # 832: +x level to [specified element] spells.
    # 843 intetionally omitted, no items
    # 865 intetionally omitted, no items
    875: lambda d: [("_block", d[0])],
    876: lambda d: [("_block", 0 - d[0])],
    # 979: +x level to elemental spells.
    979: lambda d: [],
    988: lambda d: [("_critical_resistance", d[0])],
    1020: lambda d: [],  # makabrakfire ring, also not handling this one.
    1050: lambda d: [("_area_mastery", d[0])],
    1051: lambda d: [("_single_target_mastery", d[0])],
    1052: lambda d: [("_melee_mastery", d[0])],
    1053: lambda d: [("_distance_mastery", d[0])],
    1055: lambda d: [("_berserk_mastery", d[0])],
    1056: lambda d: [("_critical_mastery", 0 - d[0])],
    1059: lambda d: [("_melee_mastery", 0 - d[0])],
    1060: lambda d: [("_distance_mastery", 0 - d[0])],
    1061: lambda d: [("_berserk_mastery", 0 - d[0])],
    1062: lambda d: [("_critical_resistance", 0 - d[0])],
    1063: lambda d: [("_rear_resistance", 0 - d[0])],
    1068: type1068,  # requires a bit more logic
    1069: type1069,  # requires a bit more logic
    1083: lambda d: [],  # light damage
    1084: lambda d: [],  # light heal
    2001: lambda d: [],  # Harvest quant, unused by solver.
}


class RawEffectInnerParams(TypedDict):
    params: list[int]
    actionId: int


class RawEffectInner(TypedDict):
    definition: RawEffectInnerParams


class RawEffectType(TypedDict):
    effect: RawEffectInner


class Effect:
    def __init__(self) -> None:
        self._transforms: list[tuple[str, int]] = []
        self._id: int

    def apply_to(self, item: EquipableItem) -> None:
        for prop, val in self._transforms:
            item.update(prop, val)

    @classmethod
    def from_raw(
        cls, raw: RawEffectType, *, is_pet: bool = False, id_: int = 0
    ) -> Effect:
        ret = cls()

        try:
            effect = raw["effect"]["definition"]
            act_id = effect["actionId"]
            transformers = _EFFECT_MAP[act_id]
            params = effect["params"]
            t = transformers(params)
            if t and params and is_pet:
                k, v = t[0]
                # dot and the gemlin line max out at lv 25
                mx_lv = 25 if id_ in {12237, 26673, 26674, 26675, 26676, 26677} else 50
                v = int(v + mx_lv * params[1])
                t = [(k, v)]
            ret._transforms = t
        except KeyError as exc:
            logging.exception(
                "Effect parsing failed skipping effect payload:\n %s",
                raw,
                exc_info=exc,
            )

        return ret


class EquipableItem:
    """
    Is any of this optimal? eh....
    Does it work quickly,
    and there are few enough items in the game where it does not matter?
    Yeeeeep.
    """

    def __init__(self) -> None:
        self._item_id: int = 0
        self._item_lv: int = 0
        self._item_rarity: int = 0
        self._item_type: int = 0
        self._title_strings: dict[str, str] = {}
        self._hp: int = 0
        self._ap: int = 0
        self._mp: int = 0
        self._wp: int = 0
        self._ra: int = 0
        self._control: int = 0
        self._block: int = 0
        self._critical_hit: int = 0
        self._dodge: int = 0
        self._lock: int = 0
        self._initiative: int = 0
        self._kit_skill: int = 0
        self._prospecting: int = 0
        self._wisdom: int = 0
        self._force_of_will: int = 0
        self._rear_mastery: int = 0
        self._healing_mastery: int = 0
        self._area_mastery: int = 0
        self._single_target_mastery: int = 0
        self._melee_mastery: int = 0
        self._distance_mastery: int = 0
        self._berserk_mastery: int = 0
        self._critical_mastery: int = 0
        self._fire_mastery: int = 0
        self._earth_mastery: int = 0
        self._water_mastery: int = 0
        self._air_mastery: int = 0
        self._mastery_1_element: int = 0
        self._mastery_2_elements: int = 0
        self._mastery_3_elements: int = 0
        self._elemental_mastery: int = 0
        self._resistance_1_element: int = 0
        self._resistance_2_elements: int = 0
        self._resistance_3_elements: int = 0
        self._fire_resistance: int = 0
        self._earth_resistance: int = 0
        self._water_resistance: int = 0
        self._air_resistance: int = 0
        self._elemental_resistance: int = 0
        self._rear_resistance: int = 0
        self._critical_resistance: int = 0
        self._armor_given: int = 0
        self._armor_received: int = 0
        self._is_shop_item: bool = False

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
        rarity = rarities.get(self._item_rarity, "???")
        typ = ITEM_TYPE_MAP[self._item_type]["title"][_locale.get()]
        return f"Item id: {self._item_id:>5} [{rarity:>10}] {typ:>20} Lv: {self._item_lv:>3} {self.name}"

    def update(self, prop_name: str, modifier: int) -> None:
        v: int = getattr(self, prop_name, 0)
        setattr(self, prop_name, v + modifier)

    @property
    def name(self) -> str | None:
        return self._title_strings.get(_locale.get(), None)

    @classmethod
    def from_bz2_bundled(cls: type[Self]) -> list[Self]:
        data_file_path = pathlib.Path(__file__).with_name("item_data.bz2")
        with bz2.open(str(data_file_path), mode="rb", compresslevel=9) as fp:
            decompressed = json.loads(fp.read())

        return [obj for element in decompressed if (obj := cls.from_json_data(element))]

    @classmethod
    def from_json_data(cls: type[Self], data: Any) -> Self | None:
        base_details = data["definition"]["item"]
        base_params = base_details["baseParameters"]
        item_type_id = base_params["itemTypeId"]

        if item_type_id in {811, 812, 511}:  # stats, sublimations, a scroll.
            return None

        if item_type_id not in ITEM_TYPE_MAP:
            logging.warning("Unknown item type %s %s", item_type_id, str(data))
            return None

        ret = cls()
        ret._title_strings = data.get("title", {}).copy()
        ret._item_id = base_details["id"]
        ret._item_lv = base_details["level"]
        if item_type_id in {582, 611}:
            ret._item_lv = 50
        ret._item_rarity = base_params["rarity"]
        ret._item_type = item_type_id
        ret._is_shop_item = 7 in base_details.get("properties", [])

        for effect_dict in data["definition"]["equipEffects"]:
            Effect.from_raw(
                effect_dict, is_pet=item_type_id in {582, 611}, id_=ret._item_id
            ).apply_to(ret)

        if ret.name is None:
            if ret._item_id not in {27700, 27701, 27702, 27703}:
                # Unknown items above, known issues though.
                logging.warning("Skipping item with id %d for lack of name", ret._item_id)
            return None

        return ret

    @cached_property
    def missing_major(self) -> bool:
        req = 0
        if self.is_epic or self.is_relic:
            req += 1

        if self.item_slot in {"NECK", "FIRST_WEAPON", "CHEST", "CAPE", "LEGS", "BACK"}:
            req += 1

        return req > self._ap + self._mp

    @cached_property
    def item_slot(self) -> str:
        return ITEM_TYPE_MAP[self._item_type]["position"][0]

    @cached_property
    def disables_second_weapon(self) -> bool:
        return self._item_type in {101, 111, 114, 117, 223, 253, 519}

    @property
    def item_type_name(self) -> str:
        return ITEM_TYPE_MAP[self._item_type]["title"][_locale.get()]

    @cached_property
    def is_relic(self) -> bool:
        return self._item_rarity == 5

    @cached_property
    def is_epic(self) -> bool:
        return self._item_rarity == 7

    @cached_property
    def is_legendary_or_souvenir(self) -> bool:
        """Here for quick selection of "best" versions"""
        return self._item_rarity in {4, 6}

    @cached_property
    def is_souvenir(self) -> bool:
        """Meh"""
        return self._item_rarity == 6

    @cached_property
    def beserk_penalty(self) -> int:
        """Quick for classes that care only about the negative"""
        return min(self._berserk_mastery, 0)

    @cached_property
    def total_elemental_res(self) -> int:
        """This is here for quick selection pre tuning"""
        return (
            +self._fire_resistance
            + self._air_resistance
            + self._water_resistance
            + self._earth_resistance
            + self._resistance_1_element
            + self._resistance_2_elements * 2
            + self._resistance_3_elements * 3
            + self._elemental_resistance * 4
        )
