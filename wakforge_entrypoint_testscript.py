"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# This is a way to test things the way wakforge uses them
import builtins
import os
import time
import zlib
from typing import Any

from msgspec import msgpack

from wakautosolver.b2048 import decode
from wakautosolver.object_parsing import get_all_items
from wakautosolver.restructured_types import ElementsEnum
from wakautosolver.versioned_entrypoints import Priority, SetMaximums, SetMinimums, StatPriority, v2Config
from wakautosolver.versioned_entrypoints import partial_solve_v2 as solve2

code1 = "ಡƸɀИযΟԛཉÛƄΕɌॷതǐĨсఖ৶ΛѵƣਨਪɆສɓ྾྾ଢƂՀદӾಏॐӧѩôԉӚਊ৮ǧ႕ȖՔఆкഖണшĤȆఝΦҡүŻҹঌఱබဇмʒโང؏ĐƅઢხॳØ"

cfg1 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=12, mp=6, wp=8, ra=0),
    objectives=StatPriority(elements=ElementsEnum.fire, rear_mastery=Priority.full_negative_only),
    dry_run=False,
    ignore_existing_items=True,
)

code2 = "ಡƸɁၒმɱନനðÑƎ೮ðɀΑǁ৴ïɐłҬऌñਯƳ༔ŦЀ྾ჱևȏऍƿലØØ"

cfg2 = v2Config(
    allowed_rarities=[4, 5, 6, 7],
    target_stats=SetMinimums(ap=13, mp=5, wp=4, ra=2),
    objectives=StatPriority(
        elements=ElementsEnum.water | ElementsEnum.air | ElementsEnum.earth, distance_mastery=Priority.prioritized
    ),
    dry_run=False,
    ignore_existing_items=False,
)


code3 = "ಡƸɁ৯যÍħലཡӄঈ४ϴ྾྾࿌ഹპྊƖòཀઓशफஉĨɚౠӱϭ৮࿈ÂԶȌΧĲƪಛǐӃဥശಛèԖઅȔ༥Ҝঙೲ૮მĠŎʁØ"

cfg3 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=6, mp=5, wp=8, ra=2),
    objectives=StatPriority(
        elements=ElementsEnum.fire,
        distance_mastery=Priority.prioritized,
        rear_mastery=Priority.full_negative_only,
    ),
    dry_run=False,
    ignore_existing_items=False,
)


code4 = "ಡƸɀИযΟԛཉÛƄΕɌॷതǐĨсఖ৶ΛѵƣਨਪɆສɓ྾྾ଢƟၿદӾಏॐӧѩôԉӚਊ৮ǧ႕ȖՔఆкഖണшĤȆఝΦҡүŻҹঌఱබဇмʒโནԛБତওണॳǀ"

cfg4 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=12, mp=6, wp=8, ra=3),
    objectives=StatPriority(
        elements=ElementsEnum.fire,
        distance_mastery=Priority.prioritized,
    ),
    dry_run=False,
    ignore_existing_items=True,
)


code5 = "ಡƸɁ৯௫ѹƂ༔Õƥഌïটζǆƈछඖǘആǁêཁ༓Ø"

cfg5 = v2Config(
    allowed_rarities=[4, 5, 6, 7],
    target_stats=SetMinimums(ap=13, mp=5, wp=6, ra=0),
    objectives=StatPriority(
        elements=ElementsEnum.fire | ElementsEnum.water | ElementsEnum.air,
        melee_mastery=Priority.prioritized,
    ),
    dry_run=False,
    ignore_existing_items=True,
)

code6 = "ಡƸɀИॠѩГཪÕळĦҙड੮ǑŀϑÕƈĉɉ୲Ì༦ØØ"

cfg6 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=13, mp=5, wp=6, ra=0),
    objectives=StatPriority(
        elements=ElementsEnum.fire,
        distance_mastery=Priority.prioritized,
    ),
    dry_run=True,
    ignore_existing_items=True,
)

code7 = "ಡƸɁ৸ĤΏʩउढϩพშɦϸၷ྾ऄǿþПဧषဦţͽ౨ϢඦɻɅϸຢͽɀØ"
cfg7 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=10, mp=3, wp=7, ra=0),
    objectives=StatPriority(),
    dry_run=False,
    ignore_existing_items=False,
)

code8 = "ಡƸɀИòѩඹངÕळĦҙड੮ǑŀϑÕƈĉɩྋ੯იઙ੪ई྾კևქऒŝɧʫഌɗËѪওক௴০ĠØ།"
cfg8 = v2Config(
    allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
    target_stats=SetMinimums(ap=13, mp=5, wp=4, ra=2),
    stats_maxs=SetMaximums(wp=4),
    objectives=StatPriority(
        distance_mastery=Priority.prioritized, elements=ElementsEnum.earth | ElementsEnum.water | ElementsEnum.air
    ),
    dry_run=False,
    ignore_existing_items=False,
)


all_codes = [code1, code2, code3, code4, code5, code6, code7, code8]
all_configs = [cfg1, cfg2, cfg3, cfg4, cfg5, cfg6, cfg7, cfg8]


def runner(*codes_and_configs: tuple[str, v2Config], loud: bool = True) -> None:
    if loud:
        os.environ["USE_TQDM"] = "1"

    err_print = builtins.print
    if not loud:

        def aprint(*values: object, sep: str | None = " ") -> None:
            pass
    else:
        aprint = builtins.print

    cc_iter = enumerate(codes_and_configs if codes_and_configs else zip(all_codes, all_configs), 1)

    for idx, (code, config) in cc_iter:
        err_print("Trying situation", idx)
        start = time.perf_counter()
        sol = solve2(build_code=code, config=config)
        stop = time.perf_counter()
        err_print(f"Time taken: {stop - start:g}s")
        items = [i for i in get_all_items() if i.item_id in sol.item_ids]
        items.sort(key=lambda i: (i.is_relic, i.is_epic, i.item_slot), reverse=True)
        if sol.error_code:
            err_print(sol.error_code)
        if sol.debug_info:
            try:
                err: list[str] | dict[str, Any] = msgpack.decode(zlib.decompress(decode(sol.debug_info), wbits=-15))
            except Exception:  # noqa: S110, BLE001
                pass
            else:
                if isinstance(err, list):
                    aprint(*err)
                if isinstance(err, dict):
                    aprint(*(f"{k}={v}" for k, v in err.items()))

        aprint(*items, sep="\n")
        if sol.build_code:
            aprint(sol.build_code)


if __name__ == "__main__":
    try:
        code = "ಡƸɀИòѩඹངÕळĦҙड੮ǑŀϑÕƈĉɩྋ੯იઙ੪ई྾კևქऒŝɧʫഌɗËѪওক௴০ĠØ།"
        cfg = v2Config(
            allowed_rarities=[1, 2, 3, 4, 5, 6, 7],
            target_stats=SetMinimums(ap=13, mp=5, wp=4, ra=2),
            stats_maxs=SetMaximums(wp=4),
            objectives=StatPriority(
                distance_mastery=Priority.prioritized, elements=ElementsEnum.earth | ElementsEnum.water | ElementsEnum.air
            ),
            dry_run=False,
            ignore_existing_items=False,
            forbidden_sources=[],  # can be any or none of ["arch", "horde", "pvp", "ultimate_boss"]
            forbidden_items=[],  # the item ids
        )

        runner((code, cfg), loud=True)
    except KeyboardInterrupt:
        pass
