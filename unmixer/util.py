import os.path
import shutil

from demucs.pretrained import _parse_remote_files, REMOTE_ROOT
from demucs.repo import BagOnlyRepo, RemoteRepo

from unmixer.constants import DEFAULT_PRETRAINED_MODELS, ISOLATED_TRACK_FORMATS


def is_isolated_track(file_path: str) -> bool:
    return os.path.splitext(file_path)[1].lower().lstrip('.') in ISOLATED_TRACK_FORMATS


def cleanup_intermediate_dir(output_dir_path: str, model_name: str) -> None:
    intermediate_dir = os.path.join(output_dir_path, model_name)
    if os.path.exists(intermediate_dir) and not os.listdir(intermediate_dir):
        print(f'Removing intermediate directory {intermediate_dir}.')
        shutil.rmtree(intermediate_dir)


def expand_path(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


# NOTE: This may break in a future version of demucs!
# Switch to using `demucs --list-models` as soon as it is available!
def get_available_pretrained_models() -> list[str]:
    try:
        models = _parse_remote_files(REMOTE_ROOT / 'files.txt')
        model_repo = RemoteRepo(models)
        bag_repo = BagOnlyRepo(REMOTE_ROOT, model_repo)
        model_names = bag_repo._bags.keys()
    except Exception as e:
        print(f'Failed to load latest pretrained models from demucs: {e}')
        model_names = DEFAULT_PRETRAINED_MODELS
    return sorted(model_names)
