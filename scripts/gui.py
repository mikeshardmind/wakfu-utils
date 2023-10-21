

import solver
from gooey import Gooey  # type: ignore

if __name__ == "__main__":

    entrypoint = Gooey(  # type: ignore
        progress_regex=r"^Progress (\d+)%$",
        hide_progress_msg=True,
    )(solver.entrypoint)
    entrypoint()