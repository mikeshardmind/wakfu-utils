import base2048
import enum
import struct
from typing import NamedTuple


class Slots(enum.IntEnum):
    R = 0
    W = 1
    G = 2
    B = 3
    RW = 4
    GR = 5
    BR = 6
    GW = 7
    BW = 8
    BG = 9
    GRW = 10
    BRW = 11
    BGR = 12
    BGW = 13
    BGRW = 14
    unset = 15


class Elements(enum.IntEnum):
    A = 0
    E = 1
    F = 2
    W = 3
    AW = 4
    EA = 5
    EW = 6
    FA = 7
    FE = 8
    FW = 9
    EAW = 10
    FAW = 11
    FEA = 12
    FEW = 13
    unset = 15


class Stats(NamedTuple):
    percent_hp: int
    res: int
    barrier: int
    heals_rec: int
    armor: int
    elemental_mastery: int
    melee_mastery: int
    distance_mastery: int
    hp: int
    lock: int
    dodge: int
    initiative: int
    lockdodge: int
    fow: int
    crit: int
    block: int
    crit_mastery: int
    rear_mastery: int
    berserk_mastery: int
    healing_mastery: int
    rear_resistence: int
    critical_resistence: int
    ap: bool
    mp: bool
    ra: bool
    wp: bool
    control: bool
    di: bool
    major_res: bool


class Item(NamedTuple):
    item_id: int
    slots: Slots
    sublimation: int
    assigned_mastery: Elements
    assigned_res: Elements


class Build(NamedTuple):
    level: int
    items: list[Item]
    stats: Stats
    relic_sub: int
    epic_sub: int


def pack_build(build: Build) -> bytes:

    return struct.pack(
        "!bb%s22b7?HH" % ("HBHBB" * len(build.items)), build.level, *build.items, build.stats, build.relic_sub, build.epic_sub
    )

def encode_build(build: Build) -> str:
    packed = pack_build(build)
    return base2048.encode(packed)

def decode_build(build_str: str) -> Build:
    ...