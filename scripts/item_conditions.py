"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from collections.abc import Sequence

import restructured_types as rst

# Manually maintained because this isn't in ankama's data.
# If ankama added items frequently, I'd make this parse a file with something like "locale,item name,lv,stat<x"
# might still do that later, idk
# lv neccessary cause of souvenirs

conditions: dict[int, Sequence[rst.Stats]] = {}

# Salty cape
block_between_40_50 = [rst.SetMinimums(block=40), rst.SetMaximums(block=50)]
for item_id in (27293, 27294):
    conditions[item_id] = block_between_40_50

# Lord Zaens's Cape, Hairlarious Cloak, Excarnus Veil (Souvenir)
crit_between_40_50 = [rst.SetMinimums(crit=40), rst.SetMaximums(crit=50)]
for item_id in (27445, 27446, 26302, 26322, 27695):
    conditions[item_id] = crit_between_40_50

# Horned Headgear, Hagen Daz's Helmet (Souvenir)
distance_between_400_500 = [rst.SetMinimums(distance_mastery=400), rst.SetMaximums(distance_mastery=500)]
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

# DigiArv Belt, Spicy Belt, Bubuckle
ap_lt_eq_11 = [rst.SetMaximums(ap=11)]
for item_id in (27447, 27448, 27303, 27304, 27409, 27410):
    conditions[item_id] = ap_lt_eq_11

# Parched Belt, Brrr Belt
ap_gt_eq_13 = [rst.SetMinimums(ap=13)]
for item_id in (26296, 26317, 27289, 27290):
    conditions[item_id] = ap_gt_eq_13

