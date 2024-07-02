"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

# This is an idealized handling that varies a bit from wakforge's. Keeping it for now
import enum
import struct
import zlib
from typing import NamedTuple

from . import b2048 as base2048
from .restructured_types import ClassesEnum as ClassName
from .restructured_types import Stats as _Stats


class ClassesEnum(enum.IntEnum):
    EMPTY = 0
    Feca = 1
    Osa = 2
    Osamodas = Osa
    Enu = 3
    Enutrof = Enu
    Sram = 4
    Xel = 5
    Xelor = Xel
    Eca = 6
    Ecaflip = Eca
    Eni = 7
    Eniripsa = Eni
    Iop = 8
    Cra = 9
    Sadi = 10
    Sadida = Sadi
    Sac = 11
    Sacrier = Sac
    Panda = 12
    Pandawa = Panda
    Rogue = 13
    Masq = 14
    Masqueraiders = Masq
    Ougi = 15
    Ouginak = Ougi
    Fog = 16
    Foggernaut = Fog
    Elio = 17
    Eliotrope = Elio
    Hupper = 18
    Huppermage = Hupper


class SlotColor(enum.IntEnum):
    R = 1
    G = 2
    B = 3
    W = 4


class Slot(NamedTuple):
    color: SlotColor
    stat_id: int
    shard_lv: int


class Elements(enum.IntFlag):
    unset = 0
    AIR = 1
    EARTH = 2
    FIRE = 4
    WATER = 8


class Stats(NamedTuple):
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

    def is_fully_allocated(self, level: int, /) -> bool:
        points = level - 1
        for lv in (25, 75, 125, 175):
            if level >= lv:
                points += 1
        return sum(self) == points

    def to_stat_values(self, cl: ClassName | None) -> _Stats:
        e_mast = self.elemental_mastery * 5
        e_mast += self.mp * 20
        e_mast += (self.ra + self.control) * 40
        wp = 6 + 2 * self.wp
        crit = self.crit
        ra = self.ra
        if cl is ClassName.Ecaflip:
            crit += 20
        if cl is ClassName.Xelor:
            wp += 6
        if cl is ClassName.Cra:
            ra += 1


        return _Stats(
            ap=6 + self.ap,
            mp=3 + self.mp,
            wp=wp,
            ra=ra,
            critical_hit=crit,
            critical_mastery=4 * self.crit_mastery,
            elemental_mastery=e_mast,
            distance_mastery=8 * self.distance_mastery,
            melee_mastery=8 * self.melee_mastery,
            rear_mastery=6 * self.rear_mastery,
            berserk_mastery=8 * self.berserk_mastery,
            healing_mastery=6 * self.healing_mastery,
            control=2 * self.control,
            fd=10 * self.di,
            lock=6 * self.lock + 4 * self.lockdodge,
            dodge=6 * self.dodge + 4 * self.lockdodge,
            block=self.block,
        )


class Item(NamedTuple):
    item_id: int
    assigned_mastery: Elements
    assigned_res: Elements
    sublimation_id: int
    slots: list[Slot]


class Build(NamedTuple):
    version_number: int
    classname: ClassesEnum
    level: int
    stats: Stats
    relic_sub: int
    epic_sub: int
    items: list[Item]
    deck: list[int]


def pack_stats(stats: Stats) -> bytes:
    *int_stats, ap, mp, ra, wp, control, di, major_res = stats

    packed_bools = 0
    for index, val in enumerate((ap, mp, ra, wp, control, di, major_res)):
        if val:
            packed_bools |= 1 << index

    return struct.pack("!23B", *int_stats, packed_bools)


def unpack_stats(packed: bytes) -> Stats:
    *int_stats, packed_bools = struct.unpack("!23B", packed)
    unpacked_bools = (bool(packed_bools & (1 << index)) for index in range(7))
    return Stats(*int_stats, *unpacked_bools)


def pack_items(items: list[Item]) -> bytes:
    # length: B (1)
    # interior, repeated length times
    # item_id: i (4)
    # assigned_mastery + assigned_res: B (1)
    # sublimation_id i (4)
    # slots: length B (1)
    # interior, repeated length times:
    # slot color: B (1)
    # stat id: B (1)
    # level: B (1)

    item_len = len(items)

    to_pack = [item_len]
    fmt_components = ["!B"]

    for item in items:
        fmt_components.append("iBiB")
        packed_resmastery = item.assigned_mastery | (item.assigned_res << 4)
        to_pack.extend((item.item_id, packed_resmastery, item.sublimation_id, len(item.slots)))
        for slot in item.slots:
            fmt_components.append("BBB")
            to_pack.extend(slot)

    return struct.pack("".join(fmt_components), *to_pack)


def unpack_items(packed: bytes) -> list[Item]:
    (_len,) = struct.unpack_from("!B", packed, 0)
    offset = 1
    ret: list[Item] = []
    for _ in range(_len):
        item_id, packed_resmastery, sublimation_id, slot_len = struct.unpack_from("!iBiB", packed, offset)
        offset += struct.calcsize("!iBiB")
        assigned_mastery = Elements(packed_resmastery & 15)
        assigned_res = Elements(packed_resmastery >> 4)

        slots: list[Slot] = []
        for _ in range(slot_len):
            slots.append(Slot(*struct.unpack_from("!BBB", packed, offset)))
            offset += struct.calcsize("!BBB")

        ret.append(Item(item_id, assigned_mastery, assigned_res, sublimation_id, slots))

    return ret


def pack_build(build: Build) -> bytes:
    # version: B (1)
    # classname.value: B (1)
    # level: H (2)
    # stats: 23s (23)
    # relic_sub: i (4)
    # epic sub: 1 (4)
    # deck: length prefixed: B (1)
    #    # repeated: active/passive id: i (4)
    # items: variable, see pack_items

    packed_items = pack_items(build.items)
    packed_stats = pack_stats(build.stats)

    fmt_str = "!BBH23siiB%di%ds" % (len(build.deck), len(packed_items))

    return struct.pack(
        fmt_str,
        build.version_number,
        build.classname,
        build.level,
        packed_stats,
        build.relic_sub,
        build.epic_sub,
        len(build.deck),
        *build.deck,
        packed_items,
    )


def unpack_build(packed: bytes) -> Build:
    base = "!BBH23siiB"
    version, classnum, level, packed_stats, relic, epic, deck_len = struct.unpack_from(base, packed, 0)
    if version != 1:
        msg = "Unknown version Number"
        raise RuntimeError(msg)
    offset = struct.calcsize(base)

    stats = unpack_stats(packed_stats)

    deck: list[int] = []

    deckfmt = "!%di" % deck_len
    deck.extend(struct.unpack_from(deckfmt, packed, offset))
    offset += struct.calcsize(deckfmt)

    packed_items = packed[offset:]
    items = unpack_items(packed_items)

    return Build(version, ClassesEnum(classnum), level, stats, relic, epic, items, deck)


def build_as_b2048(build: Build) -> str:
    packed = pack_build(build)
    compressor = zlib.compressobj(level=9, wbits=-15)
    return base2048.encode(compressor.compress(packed) + compressor.flush())


def build_from_b2048(build_str: str) -> Build:
    as_bytes = zlib.decompress(base2048.decode(build_str), wbits=-15)
    return unpack_build(as_bytes)
