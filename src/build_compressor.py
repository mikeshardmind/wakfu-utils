"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import enum

import base2048
from msgspec import Struct, msgpack


class SlotColor(enum.IntEnum):
    R = 0
    G = 1
    B = 2
    W = 3


class Slot(Struct, frozen=True, array_like=True):
    color: SlotColor
    stat_id: int | None = None
    shard_lv: int = 0


class Elements(enum.IntFlag):
    unset = 0
    AIR = 1
    EARTH = 2
    FIRE = 4
    WATER = 8


class ClassName(enum.IntEnum):
    Feca = 0
    Osa = 1
    Enu = 2
    Sram = 3
    Xel = 4
    Eca = 5
    Eni = 6
    Iop = 7
    Cra = 8
    Sadi = 9
    Sac = 10
    Panda = 11
    Rogue = 12
    Masq = 13
    Ougi = 14
    Fog = 15
    Elio = 16
    Hupper = 17


class Stats(Struct, frozen=True, array_like=True):
    percent_hp: int = 0
    res: int = 0
    barrier: int = 0
    heals_rec: int = 0
    armor: int = 0
    elemental_mastery: int = 0
    melee_mastery: int = 0
    distance_mastery: int = 0
    hp: int = 0
    lock: int = 0
    dodge: int = 0
    initiative: int = 0
    lockdodge: int = 0
    fow: int = 0
    crit: int = 0
    block: int = 0
    crit_mastery: int = 0
    rear_mastery: int = 0
    berserk_mastery: int = 0
    healing_mastery: int = 0
    rear_resistence: int = 0
    critical_resistence: int = 0
    ap: bool = False
    mp: bool = False
    ra: bool = False
    wp: bool = False
    control: bool = False
    di: bool = False
    major_res: bool = False


class Item(Struct, frozen=True, array_like=True):
    item_id: int
    assigned_mastery: Elements | None
    assigned_res: Elements | None = None
    sublimation_id: int | None = None
    slots: list[Slot] | None = None


class Build(Struct, frozen=True, array_like=True):
    classname: ClassName
    level: int
    stats: Stats
    relic_sub: int | None
    epic_sub: int | None
    items: list[Item]


def encode_build(build: Build) -> str:
    return base2048.encode(msgpack.encode(build))


def decode_build(build_str: str) -> Build:
    return msgpack.decode(base2048.decode(build_str), type=Build)
