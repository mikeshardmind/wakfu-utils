"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

import io
from pathlib import Path

import apsw
import apsw.shell

from scripts import compressed_data_gen, downloader, sqlify, structured_compressed_gen


def main() -> None:
    downloader.main()
    compressed_data_gen.main()
    sqlify.main()
    structured_compressed_gen.main()

    base_path = Path(__file__).parent.with_name("wakautosolver") / "data"
    base_path.mkdir(parents=True, exist_ok=True)
    db_path = (base_path / "items.db").resolve()
    db_dump_path = (base_path / "items.sql").resolve()

    conn = apsw.Connection(str(db_path))

    f = io.BytesIO()
    stdout = io.TextIOWrapper(f, encoding="utf-8")
    apsw_shell = apsw.shell.Shell(db=conn, stdout=stdout)
    apsw_shell.process_command(".dump")  # pyright: ignore[reportUnknownMemberType]
    conn.close()

    stdout.seek(0)
    lines = [line for line in stdout.readlines() if not line.strip().startswith("--")]
    with db_dump_path.open(mode="w", encoding="utf-8") as outpath:
        outpath.writelines(lines)


if __name__ == "__main__":
    main()
