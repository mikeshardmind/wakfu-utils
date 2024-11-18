"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

import zlib
from collections.abc import Sequence
from dataclasses import astuple, dataclass, field
from functools import partial
from itertools import compress, count
from operator import eq
from typing import Literal, NamedTuple

from . import b2048
from ._build_codes import Stats as AllocatedStats
from ._compat import decode, encode
from .object_parsing import EquipableItem
from .restructured_types import ClassesEnum as WFClasses
from .restructured_types import ElementsEnum as WFElements


class Rune(NamedTuple):
    effect_id: int = -1
    color: int = -1
    level: int = -1


class Item(NamedTuple):
    item_id: int = -1
    assignable_elements: WFElements = WFElements.empty
    rune_info: list[Rune] | None = None
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


# TEMP: see https://github.com/mikeshardmind/wakfu-utils/pull/15/files#diff-da894f04a59170295976347712c42a92da67fee89429432307a2e6cbee557c96
ITEM_REPLACEMENT_MAP = {24038: 10272, 24049: 15478, 24082: 17657, 24058: 20563, 24037: 20666, 24039: 20667}


@dataclass
class Buildv1:
    buildcodeversion: SupportedVersions = 1
    classenum: WFClasses = WFClasses.EMPTY
    level: int = 230
    # allocated stats
    s_int_percent_hp: int = 0
    s_int_elemental_res: int = 0
    s_int_barrier: int = 0
    s_int_heals_recv: int = 0
    s_int_percent_armor: int = 0
    s_str_elemental_mastery: int = 0
    s_str_melee_mastery: int = 0
    s_str_distance_mastery: int = 0
    s_str_hp: int = 0
    s_agi_lock: int = 0
    s_agi_dodge: int = 0
    s_agi_initiative: int = 0
    s_agi_lockdodge: int = 0
    s_agi_fow: int = 0
    s_fortune_percent_crit: int = 0
    s_fortune_percent_block: int = 0
    s_fortune_crit_mastery: int = 0
    s_fortune_rear_mastery: int = 0
    s_fortune_berserk_mastery: int = 0
    s_fortune_healing_mastery: int = 0
    s_fortune_rear_res: int = 0
    s_fortune_crit_res: int = 0
    s_major_ap: int = 0
    s_major_mp: int = 0
    s_major_ra: int = 0
    s_major_wp: int = 0
    s_major_control: int = 0
    s_major_damage: int = 0
    s_major_res: int = 0
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
        s = decode(zlib.decompress(b2048.decode(code), wbits=-15))
        s[1] = WFClasses(s[1])
        items = s[32:46]
        for idx, item in enumerate(items, 32):
            if not item:
                s[idx] = Item()
            else:
                item_id, elements, runes, sub = item
                # ankama deleted some duplicates
                item_id = ITEM_REPLACEMENT_MAP.get(item_id, item_id)
                if elements == [0, 0, 0]:
                    elements = WFElements.empty.value
                runes = [Rune(*r) for r in runes if r]
                s[idx] = Item(item_id, WFElements(elements), runes, sub)

        return cls(*s)

    def get_allocated_stats(self) -> AllocatedStats:
        tup = astuple(self)
        return AllocatedStats(*tup[3:32])

    def clear_items(self) -> None:
        empty = Item()
        for idx in range(1, 15):
            setattr(self, f"item_{idx}", empty)

    def _getitems(self) -> Sequence[Item]:
        return astuple(self)[32:46]

    def get_items(self) -> list[Item]:
        """
        Wakforge attaches 2 sublimations to an item matching how
        the game does it instead of the idealized structure,
        converstion to an idealized build requires knowing which sublimations
        are relic and epic sublimations, and isn't important right now.
        """
        items = self._getitems()
        # wakforge sends fake items rather than not sending them, a subarray for items would be lovely...
        return [i for i in items if i]

    def add_elements_to_item(self, item_id: int, elements: WFElements) -> None:
        for idx in range(1, 15):
            item: Item | None = getattr(self, f"item_{idx}", None)
            if item and item.item_id == item_id:
                item = Item(item.item_id, elements, item.rune_info, item.sublimation)
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

    def get_passives(self) -> list[int]:
        passives = (self.passive_1, self.passive_2, self.passive_3, self.passive_4, self.passive_5, self.passive_6)
        return [p for p in passives if p > -1]

    def get_sublimations(self) -> list[int]:
        return [
            sid
            for sid in (self.relic_sublimation_id, self.epic_sublimation_id, *(i.sublimation or -1 for i in self._getitems()))
            if sid > 0
        ]


def build_code_from_items(level: int, items: list[EquipableItem]) -> str:
    items = [i for i in items if i.item_id > 0]  # filter out placeholder items
    build = Buildv1(level=level)
    for item in items:
        build.add_item(item)

    return build_to_code(build)


def build_from_code(code: str) -> Buildv1:
    return Buildv1.from_code(code)


def build_to_code(build: Buildv1) -> str:
    b = list(astuple(build))
    b[1] = int(b[1])
    items = b[32:46]
    for idx, item in enumerate(items, 32):
        if not item:
            b[idx] = []
        else:
            item_id, elements, runes, sub = item
            runes = [tuple(r) for r in runes] if runes else []
            b[idx] = [item_id, int(elements), runes, sub]

    packed = encode(b)
    compressor = zlib.compressobj(level=9, wbits=-15)
    return b2048.encode(compressor.compress(packed) + compressor.flush())
