"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# This is a way to test things the way wakforge uses them

from wakautosolver.object_parsing import get_all_items
from wakautosolver.restructured_types import ElementsEnum
from wakautosolver.versioned_entrypoints import Priority, SetMinimums, StatPriority, v2Config
from wakautosolver.versioned_entrypoints import partial_solve_v2 as solve2

code = "ಡƸɀИযΟԛཉÛƄΕɌॷതǐĨсఖ৶ΛѵƣਨਪɆສɓ྾྾ଢƂՀદӾಏॐӧѩôԉӚਊ৮ǧ႕ȖՔఆкഖണшĤȆఝΦҡүŻҹঌఱබဇмʒโང؏ĐƅઢხॳØ"

cfg = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=12, mp=6, wp=8, ra=0),
    objectives=StatPriority(elements=ElementsEnum.fire, rear_mastery=Priority.full_negative_only),
    dry_run=False,
    ignore_existing_items=True,
)

code2 = "ಡƸɁၒმɱନനðÑƎ೮ðɀΑǁ৴ïɐłҬऌñਯƳ༔ŦЀ྾ჱևȏऍƿലØØ"

cfg2 = v2Config(
    allowed_rarities=[4, 5, 6, 7],
    target_stats=SetMinimums(ap=12, mp=6, wp=4, ra=2),
    objectives=StatPriority(
        elements=ElementsEnum.water | ElementsEnum.air | ElementsEnum.earth,
        distance_mastery=Priority.prioritized
    ),
    dry_run=False,
    ignore_existing_items=True,
)


if __name__ == "__main__":
    sol = solve2(build_code=code, config=cfg, progress_callback=print)
    items = [i for i in get_all_items() if i.item_id in sol.item_ids]
    items.sort(key=lambda i: (i.is_relic, i.is_epic, i.item_slot), reverse=True)
    print(*items, sep="\n")  # noqa: T201
