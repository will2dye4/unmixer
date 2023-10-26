from typing import Optional
import os.path
import shlex
import shutil

import demucs.separate
import ffmpeg

from unmixer.constants import (
    ALLOWED_CLIP_MODES,
    ALLOWED_WAV_BIT_DEPTHS,
    DEFAULT_CREATE_MODEL_SUBDIR,
    DEFAULT_ISOLATED_TRACK_FORMAT,
    DEFAULT_MP3_BITRATE_KBPS,
    DEFAULT_MP3_PRESET,
    DEFAULT_PRETRAINED_MODEL,
    DEFAULT_SPLIT_INPUT_INTO_SEGMENTS,
    DEFAULT_WAV_DEPTH,
    FLAC_FORMAT,
    ISOLATED_TRACK_FORMATS,
    MP3_FORMAT,
    MP3_PRESET_MAX,
    MP3_PRESET_MIN,
    OTHER_TRACK_NAME,
    WAV_FORMAT,
)
from unmixer.util import cleanup_intermediate_dir, expand_path, has_gpu_acceleration


MIX_FILTER_NAME = 'amix'


# Example: ffmpeg -i bass.wav -i drums.wav -i guitar.wav -filter_complex amix=inputs=3 -ac 2 instrumental.wav
def merge_audio_files(input_file_paths: list[str], output_file_path: str) -> None:
    if not input_file_paths or len(input_file_paths) < 2:
        raise ValueError('Not enough input files provided!')
    streams = [ffmpeg.input(expand_path(file_path)) for file_path in input_file_paths]
    ffmpeg.filter(streams, MIX_FILTER_NAME, inputs=len(streams), normalize=0). \
        output(expand_path(output_file_path), ac=2). \
        run()


# Reference: https://github.com/facebookresearch/demucs#calling-from-another-python-program
def create_isolated_tracks_from_audio_file(
        input_file_path: str, output_dir_path: str, *, remove_model_dir: Optional[bool] = None,
        other_track_name: Optional[str] = None, output_format: Optional[str] = None,
        model_name: Optional[str] = None, clip_mode: Optional[str] = None,
        disable_gpu_acceleration: Optional[bool] = None, cpu_parallelism: Optional[int] = None,
        mp3_preset: Optional[int] = None, mp3_bitrate_kbps: Optional[int] = None,
        wav_bit_depth: Optional[str] = None, split_into_segments: Optional[bool] = None,
        segment_length_seconds: Optional[int] = None, segment_overlap_percent: Optional[int] = None,
        random_shift_count: Optional[int] = None) -> None:
    input_file_path = expand_path(input_file_path)
    output_dir_path = expand_path(output_dir_path)

    if not output_format:
        output_format = DEFAULT_ISOLATED_TRACK_FORMAT
    if output_format not in ISOLATED_TRACK_FORMATS:
        raise ValueError(f'Unsupported output format "{output_format}"!')
    if output_format != MP3_FORMAT and (mp3_preset or mp3_bitrate_kbps):
        raise ValueError('MP3 preset and bitrate may only be provided when output format is MP3!')
    if output_format != WAV_FORMAT and wav_bit_depth:
        raise ValueError('WAV bit depth may only be provided when output format is WAV!')

    if clip_mode and clip_mode not in ALLOWED_CLIP_MODES:
        raise ValueError(f'Unsupported clip mode "{clip_mode}"!')

    if cpu_parallelism is not None:
        if has_gpu_acceleration() and not disable_gpu_acceleration:
            raise ValueError('CPU parallelism may only be provided when GPU acceleration is disabled!')
        if cpu_parallelism <= 0:
            raise ValueError('CPU parallelism must be a positive integer!')

    if mp3_preset and (mp3_preset < MP3_PRESET_MIN or mp3_preset > MP3_PRESET_MAX):
        raise ValueError(f'MP3 preset must be between {MP3_PRESET_MIN} and {MP3_PRESET_MAX}!')

    if mp3_bitrate_kbps and mp3_bitrate_kbps <= 0:
        raise ValueError('MP3 bitrate must be a positive integer!')

    if wav_bit_depth and wav_bit_depth not in ALLOWED_WAV_BIT_DEPTHS:
        raise ValueError(f'Unsupported WAV bit depth "{wav_bit_depth}"!')

    if split_into_segments is None:
        split_into_segments = DEFAULT_SPLIT_INPUT_INTO_SEGMENTS
    if split_into_segments:
        if segment_length_seconds and segment_length_seconds <= 0:
            raise ValueError('Segment length must be a positive integer!')
        if segment_overlap_percent and segment_overlap_percent < 0:
            raise ValueError('Segment overlap must be a nonnegative integer!')
        if random_shift_count and random_shift_count < 0:
            raise ValueError('Random shift count must be a nonnegative integer!')
    else:
        if segment_length_seconds:
            raise ValueError('Segment length may only be provided when input is split into segments!')
        if segment_overlap_percent:
            raise ValueError('Segment overlap may only be provided when input is split into segments!')
        if random_shift_count:
            raise ValueError('Random shift count may only be provided when input is split into segments!')

    print(f'Attempting to create isolated tracks from "{input_file_path}"...')
    
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path)
    
    demucs_args = [input_file_path, '--out', output_dir_path]
    if model_name:
        demucs_args.extend(['--name', model_name])
    if clip_mode:
        demucs_args.extend(['--clip-mode', clip_mode])

    if output_format == FLAC_FORMAT:
        demucs_args.append('--flac')
    elif output_format == MP3_FORMAT:
        mp3_preset = mp3_preset or DEFAULT_MP3_PRESET
        mp3_bitrate_kbps = mp3_bitrate_kbps or DEFAULT_MP3_BITRATE_KBPS
        demucs_args.extend(['--mp3', '--mp3-preset', str(mp3_preset), '--mp3-bitrate', str(mp3_bitrate_kbps)])
    elif wav_bit_depth and wav_bit_depth != DEFAULT_WAV_DEPTH:
        demucs_args.append(f'--{wav_bit_depth}')

    if split_into_segments:
        if segment_length_seconds:
            demucs_args.extend(['--segment', str(segment_length_seconds)])
        if segment_overlap_percent:
            demucs_args.extend(['--overlap', f'{(segment_overlap_percent / 100):0.2f}'])
        if random_shift_count:
            demucs_args.extend(['--shifts', str(random_shift_count)])
    else:
        demucs_args.append('--no-split')

    if disable_gpu_acceleration:
        demucs_args.extend(['--device', 'cpu'])
    if cpu_parallelism and (not has_gpu_acceleration() or disable_gpu_acceleration):
        demucs_args.extend(['--jobs', str(cpu_parallelism)])

    print(f'Invoking demucs with args: {shlex.join(demucs_args)}')
    demucs.separate.main(demucs_args)
    
    # demucs creates an intermediate directory for the model name.
    # Move the isolated tracks out of this directory if desired.
    if remove_model_dir is None:
        remove_model_dir = not DEFAULT_CREATE_MODEL_SUBDIR
    file_name = os.path.splitext(os.path.basename(input_file_path))[0]
    model_name = model_name or DEFAULT_PRETRAINED_MODEL

    if remove_model_dir:
        output_dir = os.path.join(output_dir_path, file_name)
        shutil.move(os.path.join(output_dir_path, model_name, file_name), output_dir)
        cleanup_intermediate_dir(output_dir_path, model_name)
    else:
        output_dir = os.path.join(output_dir_path, model_name, file_name)

    print(f'Wrote isolated tracks to "{output_dir}".')
    
    if other_track_name and (other_track := next((n for n in os.listdir(output_dir) if n.startswith(OTHER_TRACK_NAME)), None)):
        _, extension = os.path.splitext(other_track)
        shutil.move(os.path.join(output_dir, other_track), os.path.join(output_dir, other_track_name + extension))
