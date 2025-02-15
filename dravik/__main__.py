import os

from dravik.app import Dravik


app = Dravik(config_dir=os.environ.get("DRAVIK_DIR", "") or None)
run = app.run

if __name__ == "__main__":
    run()
