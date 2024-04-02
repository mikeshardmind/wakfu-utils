"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import zlib
from functools import partial
from itertools import compress, count
from operator import eq
from typing import Literal

from msgspec import Struct, field, msgpack
from msgspec.structs import astuple

from . import b2048
from ._build_codes import Stats as AllocatedStats
from ._typing_memes import STAT_MAX, UP_TO_5, UP_TO_10, UP_TO_20, UP_TO_40, ZERO_OR_ONE
from .object_parsing import EquipableItem
from .restructured_types import ClassesEnum as WFClasses
from .restructured_types import ElementsEnum as WFElements


class Rune(Struct, array_like=True):
    effect_id: int = -1
    color: int = -1
    level: int = -1


class Item(Struct, array_like=True):
    item_id: int = -1
    assignable_elements: WFElements = WFElements.empty
    rune_info: list[Rune] = field(default_factory=lambda: [Rune() for _ in range(4)])
    sublimation: int = -1

    def __bool__(self):
        return self.item_id > 0


SupportedVersions = Literal[1]


v1BuildSlotsOrder = [
    "ACCESSORY",
    "BACK",
    "BELT",
    "CHEST",
    "FIRST_WEAPON",
    "HEAD",
    "LEFT_HAND",
    "LEGS",
    "MOUNT",
    "NECK",
    "PET",
    "LEFT_HAND",  # RIGHT_HAND, but ...
    "SECOND_WEAPON",
    "SHOULDERS",
]


class Buildv1(Struct, array_like=True):
    buildcodeversion: SupportedVersions = 1
    classenum: WFClasses = WFClasses.EMPTY
    level: int = 230
    # allocated stats
    s_int_percent_hp: STAT_MAX = 0
    s_int_elemental_res: UP_TO_10 = 0
    s_int_barrier: UP_TO_10 = 0
    s_int_heals_recv: UP_TO_5 = 0
    s_int_percent_armor: UP_TO_10 = 0
    s_str_elemental_mastery: STAT_MAX = 0
    s_str_melee_mastery: UP_TO_40 = 0
    s_str_distance_mastery: UP_TO_40 = 0
    s_str_hp: STAT_MAX = 0
    s_agi_lock: STAT_MAX = 0
    s_agi_dodge: STAT_MAX = 0
    s_agi_initiative: UP_TO_20 = 0
    s_agi_lockdodge: STAT_MAX = 0
    s_agi_fow: UP_TO_20 = 0
    s_fortune_percent_crit: UP_TO_20 = 0
    s_fortune_percent_block: UP_TO_20 = 0
    s_fortune_crit_mastery: STAT_MAX = 0
    s_fortune_rear_mastery: STAT_MAX = 0
    s_fortune_berserk_mastery: STAT_MAX = 0
    s_fortune_healing_mastery: STAT_MAX = 0
    s_fortune_rear_res: UP_TO_20 = 0
    s_fortune_crit_res: UP_TO_20 = 0
    s_major_ap: ZERO_OR_ONE = 0
    s_major_mp: ZERO_OR_ONE = 0
    s_major_ra: ZERO_OR_ONE = 0
    s_major_wp: ZERO_OR_ONE = 0
    s_major_control: ZERO_OR_ONE = 0
    s_major_damage: ZERO_OR_ONE = 0
    s_major_res: ZERO_OR_ONE = 0
    item_1: Item | list[object] = field(default_factory=list)
    item_2: Item | list[object] = field(default_factory=list)
    item_3: Item | list[object] = field(default_factory=list)
    item_4: Item | list[object] = field(default_factory=list)
    item_5: Item | list[object] = field(default_factory=list)
    item_6: Item | list[object] = field(default_factory=list)
    item_7: Item | list[object] = field(default_factory=list)
    item_8: Item | list[object] = field(default_factory=list)
    item_9: Item | list[object] = field(default_factory=list)
    item_10: Item | list[object] = field(default_factory=list)
    item_11: Item | list[object] = field(default_factory=list)
    item_12: Item | list[object] = field(default_factory=list)
    item_13: Item | list[object] = field(default_factory=list)
    item_14: Item | list[object] = field(default_factory=list)
    active_1: int = -1
    active_2: int = -1
    active_3: int = -1
    active_4: int = -1
    active_5: int = -1
    active_6: int = -1
    active_7: int = -1
    active_8: int = -1
    active_9: int = -1
    active_10: int = -1
    active_11: int = -1
    active_12: int = -1
    passive_1: int = -1
    passive_2: int = -1
    passive_3: int = -1
    passive_4: int = -1
    passive_5: int = -1
    passive_6: int = -1
    epic_sublimation_id: int = -1
    relic_sublimation_id: int = -1

    @classmethod
    def from_code(cls, code: str) -> Buildv1:
        # wakforge sending empty arrays...
        s = msgpack.decode(zlib.decompress(b2048.decode(code), wbits=-15))
        s[1] = WFClasses(s[1])
        items = s[32:46]
        for idx, item in enumerate(items, 32):
            if not item:
                s[idx] = Item()
            else:
                item_id, elements, runes, subs = item
                if item_id == -1:
                    s[idx] = Item()
                    continue
                runes = [Rune() for r in runes if r]
                s[idx] = Item(item_id, WFElements(elements), runes, subs)

        return cls(*s)

    def get_allocated_stats(self) -> AllocatedStats:
        tup = astuple(self)
        return AllocatedStats(*tup[3:32])

    def clear_items(self) -> None:
        empty = Item()
        for idx in range(1, 15):
            setattr(self, f"item_{idx}", empty)

    def get_items(self) -> list[Item]:
        """
        Wakforge attaches 2 sublimations to an item matching how
        the game does it instead of the idealized structure,
        converstion to an idealized build requires knowing which sublimations
        are relic and epic sublimations, and isn't important right now.
        """
        items = astuple(self)[32:46]
        # wakforge sends fake items rather than not sending them, a subarray for items would be lovely...
        return [i for i in items if isinstance(i, Item) and i]

    def add_elements_to_item(self, item_id: int, elements: WFElements) -> None:
        for idx in range(1, 15):
            item: Item | None = getattr(self, f"item_{idx}", None)
            if item and item.item_id == item_id:
                item.assignable_elements = elements
                setattr(self, f"item_{idx}", item)
                break

    def add_item(self, item: EquipableItem, elements: WFElements = WFElements.empty, /) -> None:
        indices = compress(count(1), map(partial(eq, item.item_slot), v1BuildSlotsOrder))
        for index in indices:
            if not getattr(self, f"item_{index}", None):
                setattr(self, f"item_{index}", Item(item_id=item.item_id, assignable_elements=elements))
                break
        else:
            msg = f"Can't find a valid slot for this thing. {item}"
            raise RuntimeError(msg)

    def to_code(self) -> str:
        packed = msgpack.encode(self)
        compressor = zlib.compressobj(level=9, wbits=-15)
        return b2048.encode(compressor.compress(packed) + compressor.flush())

    def get_passives(self) -> list[int]:
        passives = (self.passive_1, self.passive_2, self.passive_3, self.passive_4, self.passive_5, self.passive_6)
        return [p for p in passives if p > -1]


def build_code_from_items(level: int, items: list[EquipableItem]) -> str:
    items = [i for i in items if i.item_id > 0]  # filter out placeholder items
    build = Buildv1(level=level)
    for item in items:
        build.add_item(item)
    packed = msgpack.encode(build)
    compressor = zlib.compressobj(level=9, wbits=-15)
    return b2048.encode(compressor.compress(packed) + compressor.flush())


def build_from_code(code: str) -> Buildv1:
    return Buildv1.from_code(code)
