from typing import Optional
import os.path
import shutil

from demucs.pretrained import DEFAULT_MODEL
import demucs.separate
import ffmpeg

from unmixer.constants import OTHER_TRACK_NAME
from unmixer.util import cleanup_intermediate_dir


DEFAULT_MP3_PRESET = '2'  # range: 2 (best quality) --> 7 (fastest)

MIX_FILTER_NAME = 'amix'


# Example: ffmpeg -i bass.wav -i drums.wav -i guitar.wav -filter_complex amix=inputs=3 -ac 2 instrumental.wav
def merge_audio_files(input_file_paths: list[str], output_file_path: str) -> None:
    if not input_file_paths or len(input_file_paths) < 2:
        raise ValueError('Not enough input files provided!')
    streams = [ffmpeg.input(os.path.expanduser(file_path)) for file_path in input_file_paths]
    ffmpeg.filter(streams, MIX_FILTER_NAME, inputs=len(streams), normalize=0). \
        output(os.path.expanduser(output_file_path), ac=2). \
        run()


# Reference: https://github.com/facebookresearch/demucs#calling-from-another-python-program
def create_isolated_tracks_from_audio_file(input_file_path: str, output_dir_path: str,
                                           other_track_name: Optional[str] = None,
                                           output_mp3_format: bool = False) -> None:
    input_file_path = os.path.expanduser(input_file_path)
    output_dir_path = os.path.expanduser(output_dir_path)
    print(f'Attempting to create isolated tracks from "{input_file_path}"...')
    
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)
    
    demucs_args = [input_file_path, '--out', output_dir_path]
    if output_mp3_format:
        demucs_args.extend(['--mp3', '--mp3-preset', DEFAULT_MP3_PRESET])

    demucs.separate.main(demucs_args)
    
    # demucs creates an intermediate directory for the model name.
    # Move the isolated tracks out of this directory.
    file_name = os.path.splitext(os.path.basename(input_file_path))[0]
    output_dir = os.path.join(output_dir_path, file_name)
    shutil.move(os.path.join(output_dir_path, DEFAULT_MODEL, file_name), output_dir)
    print(f'Wrote isolated tracks to "{output_dir}".')
    cleanup_intermediate_dir(output_dir_path)
    
    if other_track_name and (other_track := next((n for n in os.listdir(output_dir) if n.startswith(OTHER_TRACK_NAME)), None)):
        _, extension = os.path.splitext(other_track)
        shutil.move(os.path.join(output_dir, other_track), os.path.join(output_dir, other_track_name + extension))
