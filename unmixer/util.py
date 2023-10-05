import os.path

from unmixer.constants import ISOLATED_TRACK_FORMATS


def is_isolated_track(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower().lstrip('.') in ISOLATED_TRACK_FORMATS
