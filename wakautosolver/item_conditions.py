"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache, reduce
from operator import and_

from . import restructured_types as rst
from .object_parsing import EquipableItem

# Manually maintained because this isn't in ankama's data.
# If ankama added items frequently, I'd make this parse a file with something like "locale,item name,lv,stat<x"
# might still do that later, idk
# lv neccessary cause of souvenirs

conditions: dict[int, Sequence[rst.Stats]] = {}
NEGCRIT = rst.SetMinimums(critical_hit=-10)

# Salty cape
block_between_40_50 = [rst.SetMinimums(block=40), rst.SetMaximums(block=50)]
for item_id in (27293, 27294):
    conditions[item_id] = block_between_40_50

# Lord Zaens's Cape, Hairlarious Cloak, Excarnus Veil (Souvenir)
crit_between_40_50 = [rst.SetMinimums(critical_hit=40), rst.SetMaximums(critical_hit=50)]
for item_id in (27445, 27446, 26302, 26322, 27695):
    conditions[item_id] = crit_between_40_50

# Horned Headgear, Hagen Daz's Helmet (Souvenir)
distance_between_400_500 = [
    rst.SetMinimums(distance_mastery=400),
    rst.SetMaximums(distance_mastery=500),
]
for item_id in (26292, 26313, 27747):
    conditions[item_id] = distance_between_400_500

# Amon Amarth Breastplate 400 <= Lock <= 500
lock_between_400_500 = [rst.SetMinimums(lock=400), rst.SetMaximums(lock=500)]
for item_id in (27443, 27444):
    conditions[item_id] = lock_between_400_500

# Jeering Epaulettes	500 <= Dodge <= 600
dodge_between_500_600 = [rst.SetMinimums(dodge=500), rst.SetMaximums(dodge=600)]
for item_id in (26304, 26324):
    conditions[item_id] = dodge_between_500_600

# Breastplate of Shadows, Biddyplate, Dehydrated Breastplate, Shademail
lock_between_500_600 = [rst.SetMinimums(lock=500), rst.SetMaximums(lock=600)]
for item_id in (26299, 26318, 26953, 26954, 27297, 27298, 26290, 26311):
    conditions[item_id] = lock_between_500_600

# DigiArv Belt, Spicy Belt, Bubuckle, Trool Warrior Spikes, Ancient Trool Warrior Spikes
ap_lt_eq_11 = [rst.SetMaximums(ap=11)]
for item_id in (27447, 27448, 27303, 27304, 27409, 27410, 18691, 30138):
    conditions[item_id] = ap_lt_eq_11

# Parched Belt, Brrr Belt
ap_gt_eq_13 = [rst.SetMinimums(ap=13)]
for item_id in (26296, 26317, 27289, 27290):
    conditions[item_id] = ap_gt_eq_13

# Cape Hillary
block_lt_eq_20 = [rst.SetMaximums(block=20)]
for item_id in (26291, 26312):
    conditions[item_id] = block_lt_eq_20

# mocking cap
crit_lt_eq_25 = [rst.SetMaximums(critical_hit=25)]
for item_id in (26303, 26323):
    conditions[item_id] = crit_lt_eq_25

# worn to a shadow
control_eq_4 = [rst.SetMinimums(control=4), rst.SetMaximums(control=4)]
for item_id in (26293, 26314):
    conditions[item_id] = control_eq_4

# hazepaulettes, krock tails, hooklettes, white crow hackle (souv)
mp_lt_eq_5 = [rst.SetMaximums(mp=5)]
for item_id in (27449, 27450, 26997, 26998, 26289, 26310, 27693):
    conditions[item_id] = mp_lt_eq_5

# World Maps, Hairpin, Art'And Cards
ra_lt_eq_3 = [rst.SetMaximums(ra=3)]
for item_id in (27299, 27300, 26295, 26316, 27377, 27378):
    conditions[item_id] = ra_lt_eq_3

# Ax of Reason
ra_gt_eq_2 = [rst.SetMinimums(ra=2)]
for item_id in (27287, 27288):
    conditions[item_id] = ra_gt_eq_2

# Shadowed Boots
wp_lt_eq_4 = [rst.SetMaximums(wp=4)]
for item_id in (26298,):
    conditions[item_id] = wp_lt_eq_4

# Tell-Tale Boots, Laughing Shovel
wp_gt_eq_8 = [rst.SetMinimums(wp=8)]
for item_id in (26994, 26995, 26996, 26300, 26319):
    conditions[item_id] = wp_gt_eq_8


@lru_cache(1024)
def get_item_conditions(
    item: EquipableItem,
) -> tuple[rst.SetMinimums | None, rst.SetMaximums | None]:
    item_conds = conditions.get(item.item_id, [])
    set_mins: list[rst.SetMinimums] = []
    set_maxs: list[rst.SetMaximums] = []

    for c in item_conds:
        if isinstance(c, rst.SetMinimums):
            set_mins.append(c)
        elif isinstance(c, rst.SetMaximums):
            set_maxs.append(c)

    mins = None
    if len(set_mins) == 1:
        mins = set_mins[0]
    elif set_mins:
        mins = reduce(and_, set_mins)
    maxs = None
    if len(set_maxs) == 1:
        maxs = set_maxs[0]
    elif set_maxs:
        maxs = reduce(and_, set_maxs)
    return mins, maxs
