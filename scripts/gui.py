"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

Copyright (C) 2023 Michael Hall <https://github.com/mikeshardmind>
"""

# TODO: replace this with something much better

import solver
from gooey import Gooey  # type: ignore

if __name__ == "__main__":
    entrypoint = Gooey(  # type: ignore
        progress_regex=r"^Progress (\d+)%$",
        hide_progress_msg=True,
    )(solver.entrypoint)
    entrypoint()
