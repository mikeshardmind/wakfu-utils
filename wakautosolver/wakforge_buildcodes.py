"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import enum
from typing import Literal

from msgspec import Struct, field

from ._typing_memes import STAT_MAX, UP_TO_5, UP_TO_10, UP_TO_11, UP_TO_20, UP_TO_40, ZERO_OR_ONE

# Builds here are currently equivalent to an open PR, do not use for stable


class WFClasses(enum.IntEnum):
    feca = 0
    osamodas = 1
    enutrof = 2
    sram = 3
    xelor = 4
    ecaflip = 5
    eniripsa = 6
    iop = 7
    cra = 8
    sadida = 9
    sacrier = 10
    pandawa = 11
    rogue = 12
    masqueraider = 13
    ouginak = 14
    foggernaut = 15
    eliotrope = 16
    huppermage = 17


class WFElements(enum.IntFlag):
    empty = 0
    fire = 1 << 1
    earth = 1 << 2
    water = 1 << 3
    air = 1 << 4


class Rune(Struct, array_like=True):
    effect_id: int | None = None
    color: int | None = None
    level: UP_TO_11 = 0


class Item(Struct, array_like=True):
    item_id: int = -1
    assignable_elements: WFElements = WFElements.empty
    rune_info: list[Rune] = field(default_factory=lambda: [Rune() for _ in range(4)])
    sublimations: list[int] = field(default_factory=lambda: [0, 0])


SupportedVersions = Literal[1]


class Buildv1(Struct, array_like=True):
    buildcodeversion: SupportedVersions = 1
    classenum: WFClasses = WFClasses.feca
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
    item_1: Item = field(default_factory=Item)
    item_2: Item = field(default_factory=Item)
    item_3: Item = field(default_factory=Item)
    item_4: Item = field(default_factory=Item)
    item_5: Item = field(default_factory=Item)
    item_6: Item = field(default_factory=Item)
    item_7: Item = field(default_factory=Item)
    item_8: Item = field(default_factory=Item)
    item_9: Item = field(default_factory=Item)
    item_10: Item = field(default_factory=Item)
    item_11: Item = field(default_factory=Item)
    item_12: Item = field(default_factory=Item)
    item_13: Item = field(default_factory=Item)
    item_14: Item = field(default_factory=Item)
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
