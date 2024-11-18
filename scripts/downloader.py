"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

import asyncio
import os
import pathlib
from typing import Any, Optional

import aiohttp

_FTYPES = (
    "items",
    "actions",
    "equipmentItemTypes",
    "states",
    "itemProperties",
    "recipeCategories",
    "recipes",
    "harvestLoots",
    "itemTypes",
    "blueprints",
    "recipeResults",
)


#: Available for checking if version is known to work with object_parsing code
VERSIONS_TESTED = ("1.81.1.13", "1.81.1.15", "1.83.1.21", "1.83.1.23", "1.85.1.29")


async def _grab_file(
    session: aiohttp.ClientSession,
    result_map: dict[str, Any],
    version: str,
    file_type: str,
) -> None:
    URL = f"https://wakfu.cdn.ankama.com/gamedata/{version}/{file_type}.json"
    async with session.get(URL) as r:
        data = await r.text()
        result_map[file_type] = data


async def networking(specific_files: Optional[list[str]] = None) -> None:
    file_types = _FTYPES if not specific_files else tuple(f for f in _FTYPES if f in specific_files)

    async with aiohttp.ClientSession() as session:
        ver = os.environ.get("WAKFU_VERSION") or None

        if not ver:
            async with session.get("https://wakfu.cdn.ankama.com/gamedata/config.json") as r:
                data = await r.json()
                ver = data["version"]

        results: dict[str, Any] = {}
        coros = {_grab_file(session, results, ver, file_type) for file_type in file_types}
        await asyncio.gather(*coros)

    base_path = pathlib.Path(__file__).with_name("json_data")
    base_path.mkdir(parents=True, exist_ok=True)

    for name, data in results.items():
        path = base_path / f"{name}.json"
        with path.open(mode="w", encoding="utf-8") as fp:
            fp.write(data)


def main():
    asyncio.run(networking())


if __name__ == "__main__":
    main()
