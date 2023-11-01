"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

### Exists for wakforge

@dataclass(frozen=True, kw_only=True)
class Config:
    lv: int
    ap: int = 5
    mp: int = 2
    wp: int = 0
    ra: int = 0
    num_mastery: int = 3
    dist: bool = False
    melee: bool = False
    zerk: bool = False
    rear: bool = False
    heal: bool = False
    unraveling: bool = False
    skipshields: bool = True
    lwx: bool = False
    bcrit: int = 0
    bmast: int = 0
    bcmast: int = 0
    forbid: list[str] = field(default_factory=list)
    idforbid: list[int] = field(default_factory=list)
    idforce: list[int] = field(default_factory=list)
    twoh: bool = False
    skiptwo_hand: bool = False
    locale: Literal["en"] = "en"
    dry_run: bool = False
    hard_cap_depth: int = 100
    negzerk: Literal["full", "half", "none"] = "half"
    negrear: Literal["full", "half", "none"] = "none"


ClassNames = Literal[
    "Feca",
    "Osa",
    "Enu",
    "Sram",
    "Xel",
    "Eca",
    "Eni",
    "Iop",
    "Cra",
    "Sadi",
    "Sac",
    "Panda",
    "Rogue",
    "Masq",
    "Ougi",
    "Fog",
    "Elio",
    "Hupper",
]

#: (ReturnValue, Error)
Result = tuple[list[int] | None, str | None]


def solve(*args: Any, **kwargs: Any) -> Any:
    ...# TODO, wrap new entrypoint for old behavior


def solve_config(config: Config) -> Result:
    try:
        solution = solve(config, no_sys_exit=True, no_print_log=True)
    except Exception as e:
        return (None, e.args[0])
    else:
        if solution:
            best = solution[0]
            _score, _text, items = best
            return [i._item_id for i in items], None
        return None, "No possible solution found"


def v1_lv_class_solve(
    level: int,
    class_: ClassNames,
    num_elements: int = 3,
    dist: bool = False,
    melee: bool = False,
    force_items: list[int] | None = None,
    forbid_items: list[int] | None = None,
) -> Result:
    """
    Quick thing provided for wakforge to be "quickly up and running" with pyiodide before the monoserver launch
    """
    #: This is this way because pyodide proxies aren't lists,
    #: and I want this to work pyodide or python caller
    force_items = [*(i for i in (force_items if force_items else []))]
    forbid_items = [*(i for i in (forbid_items if forbid_items else []))]

    if level not in range(20, 231, 15):
        return (None, "autosolver only solves on als levels currently")

    crit = 0 if class_ in ("Panda", "Feca") else 20
    ap = 5
    mp = 2
    ra = 0
    if class_ == "Xel":
        mp = 1
    if class_ in ("Xel", "Enu", "Eni", "Cra", "Sadi"):
        if level >= 155:
            ra = 3
        elif level >= 125:
            ra = 2
        elif level >= 50:
            ra = 1

    if class_ == "Elio" and level >= 125:
        ra = 2
        mp = 1

    if class_ in ("Sram", "Iop", "Ougi", "Sac"):
        ra = -1

    if level < 50:
        ap = 2
        mp = 1

    rear = bool(class_ == "Sram")
    zerk = bool(class_ == "Sac")
    heal = bool(class_ == "Eni" and level >= 125)

    config = Config(
        lv=level,
        bcrit=crit,
        dist=dist,
        melee=melee,
        rear=rear,
        zerk=zerk,
        heal=heal,
        ap=ap,
        mp=mp,
        ra=ra,
        wp=0,
        num_mastery=num_elements,
        idforce=force_items,
        idforbid=forbid_items,
        hard_cap_depth=7,
    )

    return solve_config(config)