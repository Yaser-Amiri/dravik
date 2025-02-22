import os

from dravik.app import Dravik

app = Dravik(config_dir=os.environ.get("DRAVIK_DIR", "") or None)
run_app = app.run
init = app.services.create_configs


if __name__ == "__main__":
    run_app()
