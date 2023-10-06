import os.path
import shutil

from demucs.pretrained import DEFAULT_MODEL

from unmixer.constants import ISOLATED_TRACK_FORMATS


def is_isolated_track(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower().lstrip('.') in ISOLATED_TRACK_FORMATS


def cleanup_intermediate_dir(output_dir_path: str) -> None:
    intermediate_dir = os.path.join(output_dir_path, DEFAULT_MODEL)
    if os.path.exists(intermediate_dir) and not os.listdir(intermediate_dir):
        print(f'Removing intermediate directory {intermediate_dir}.')
        shutil.rmtree(intermediate_dir)
