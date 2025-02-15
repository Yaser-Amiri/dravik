import os
from functools import partial
import asyncio

from dravik.app import Dravik

app = Dravik(config_dir=os.environ.get("DRAVIK_DIR", "") or None)
run_app = app.run

if __name__ == "__main__":
    run_app()
else:
    # workaround to avoid "coroutine not awaited"  for now, a proper cli will be needed.
    init = partial(asyncio.run, app.services.create_configs())
