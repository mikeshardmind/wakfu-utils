"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from msgspec.structs import replace

from wakautosolver.build_codes import ClassName, Elements, Item, Stats, encode_build
from wakautosolver.build_codes import v1Build as Build

if __name__ == "__main__":
    stats = Stats(
        percent_hp=33,
        res=10,
        distance_mastery=40,
        elemental_mastery=2,
        fow=20,
        dodge=22,
        crit=20,
        crit_mastery=22,
        ap=True,
        di=True,
        major_res=True,
    )

    ele3 = Elements.AIR | Elements.FIRE | Elements.EARTH
    ele2 = Elements.FIRE | Elements.AIR

    items = [
        Item(21207, ele3),
        Item(26599, ele2),
        Item(25075, ele3),
        Item(22371, ele2),
        Item(26620, ele2),
        Item(22407, ele2),
        Item(26020),
        Item(26756),
        Item(22383, ele2),
        Item(25804),
        Item(25970),
        Item(19055, ele3),
    ]

    # No active support in deck yet
    passives = [7340, 7336, 7328, 7335, 5144]

    build = Build(ClassName.Osamodas, 170, stats, items=items, deck=passives)
    encoded = encode_build(build)

    # 78 ઞԸƍஏයȥťആïɉकƐҜƄƀഓňऋΘİ၃༡३ҠĶҿҍԇदƯİǃЯ٤০ඦѺന؏Ή၆ǂĿႻႭùವႻஅїɀ࿉Ҟഒʙ၊ॸʧǃ༗ʅ৪හ࿂ഢཛϻඬмЃмȰфɾуǐ২།
    print(len(encoded), encoded)

    # if we instead treat the deck as not tied to a build since decks may be changed more freely than gear
    # people can share their in game deck codes + wakforge build code
    build = replace(build, deck=[])
    encoded = encode_build(build)
    # 67 ઞԸƍஏයȥťആïɉकƐҜƄƀഓňऋΘİ၃༡३ҠĶҿҍԇदƯİǃЯ٤০ඦѺന؏Ή၆ǂĿႻႭùವႻஅїɀ࿉Ҟഒʙ၊ॸʧǃ༗ʅ৪හ࿂൮༕ǀ
    print(len(encoded), encoded)