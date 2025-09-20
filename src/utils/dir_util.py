import sys
from pathlib import Path


def get_exe_dir_storage(storage_dir_name, relative_dir):
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_dir = Path(sys._MEIPASS).parent
        else:
            base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent

    storage_dir = base_dir / storage_dir_name
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / relative_dir
