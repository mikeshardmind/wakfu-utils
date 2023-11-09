"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

import enum
import zlib

from msgspec import Struct, field, msgpack

from . import b2048 as base2048
from .restructured_types import Stats as _Stats


class SlotColor(enum.IntEnum):
    R = 1
    G = 2
    B = 3
    W = 4


class Slot(Struct, array_like=True):
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


class Stats(Struct, array_like=True):
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

    def to_stat_values(self, is_xelor: bool = False) -> _Stats:
        e_mast = self.elemental_mastery * 5
        e_mast += self.mp * 20
        e_mast += (self.ra + self.control) * 40
        wp = 12 if is_xelor else 6
        wp += 2 * self.wp
        return _Stats(
            ap=6 + self.ap,
            mp=3 + self.mp,
            wp=wp,
            ra=1 * self.ra,
            crit=self.crit,
            crit_mastery=4 * self.crit_mastery,
            elemental_mastery=e_mast,
            distance_mastery=8 * self.distance_mastery,
            melee_mastery=8 * self.melee_mastery,
            rear_mastery=6 * self.rear_mastery,
            beserk_mastery=8 * self.berserk_mastery,
            heal_mastery=6 * self.healing_mastery,
            control=2 * self.control,
            fd=10 * self.di,
            lock=6 * self.lock + 4 * self.lockdodge,
            dodge=6 * self.dodge + 4 * self.lockdodge,
            block=self.block,
        )


class Item(Struct, array_like=True):
    item_id: int
    assigned_mastery: Elements = Elements.unset
    assigned_res: Elements = Elements.unset
    sublimation_id: int | None = None
    slots: list[Slot] | None = None


class Build(Struct, array_like=True):
    classname: ClassName | None = None
    level: int = 230
    stats: Stats = field(default_factory=Stats)
    relic_sub: int | None = None
    epic_sub: int | None = None
    items: list[Item] = field(default_factory=list)
    deck: list[int] = field(default_factory=list)


def encode_build(build: Build) -> str:
    return base2048.encode(zlib.compress(msgpack.encode(build), level=9, wbits=-15))


def decode_build(build_str: str) -> Build:
    return msgpack.decode(zlib.decompress(base2048.decode(build_str), wbits=-15), type=Build)


# TODO: RELEASE-BLOCKER Add element support to the below prior to next release, or remove the code.
# Do not version this without element support.
def encode_partialv1(
    classname: str | ClassName | None = None,
    level: int = 230,
    items: list[int] | None = None,
) -> str:
    if isinstance(classname, str):
        try:
            classname = ClassName[classname]
        except KeyError:
            return ""
    _items = [Item(item_id=i) for i in items] if items else []

    build = Build(classname=classname, level=level, items=_items)

    return encode_build(build)


DATA = tuple[ClassName | None, int, list[int]]
Decodev1Result = tuple[DATA | None, str | None]


def decode_partialv1(build_str: str) -> Decodev1Result:
    try:
        build = decode_build(build_str)
    except Exception:  # noqa: BLE001
        return None, "Invalid Build String"

    return (build.classname, build.level, [item.item_id for item in build.items]), None
