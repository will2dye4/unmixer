#!/usr/bin/env python

from typing import Optional
import argparse
import os
import os.path
import sys

from unmixer.constants import DEFAULT_OUTPUT_DIR, GUITAR_TRACK_NAME, PIANO_TRACK_NAME
from unmixer.ui import UnmixerUI
from unmixer.util import is_isolated_track


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='create and explore isolated tracks from music files')
    
    parser.add_argument('music_file_or_track_dir', nargs='?',
                        help='path to the file to unmix, or path to a directory containing isolated tracks')
    parser.add_argument('--mp3', '--output-mp3', action='store_true',
                        help='output isolated tracks as MP3 files instead of WAV')
    parser.add_argument('-o', '--output', '--output-dir',
                        help=f'path to the directory for output isolated tracks (default: {DEFAULT_OUTPUT_DIR})')
    
    other_track_group = parser.add_mutually_exclusive_group()
    other_track_group.add_argument('-g', '--guitar', action='store_true', help='show "Guitar" track instead of "Other"')
    other_track_group.add_argument('-p', '--piano', action='store_true', help='show "Piano" track instead of "Other"')
    
    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]
    
    config = parse_args(args)
    input_dir_path = None
    output_dir_path = None
    song_path = None
    other_track_name = None
    
    if path := config.music_file_or_track_dir:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            print(f'Failed to locate "{path}"!', file=sys.stderr)
            sys.exit(1)
        if os.path.isdir(path):
            # Exploring existing isolated tracks
            if len([f for f in os.listdir(path) if is_isolated_track(f)]) < 2:
                print(f'Not enough isolated tracks to explore in "{path}"!', file=sys.stderr)
                sys.exit(1)
            input_dir_path = path
        else:
            # Creating new isolated tracks from a song (or no song provided, which will prompt the user to choose)
            song_path = path
    
    if config.output:
        if path and os.path.isdir(path):
            print(f'Output directory may only be provided when creating isolated tracks!', file=sys.stderr)
            sys.exit(1)
        else:
            output_dir_path = os.path.abspath(os.path.expanduser(config.output))
    
    output_mp3_format = False
    if config.mp3:
        if path and os.path.isdir(path):
            print(f'Output format may only be provided when creating isolated tracks!', file=sys.stderr)
            sys.exit(1)
        else:
            output_mp3_format = config.mp3
    
    if config.guitar:
        other_track_name = GUITAR_TRACK_NAME
    elif config.piano:
        other_track_name = PIANO_TRACK_NAME
    
    print('Launching Unmixer UI...')
    UnmixerUI(song_path=song_path, input_dir_path=input_dir_path,
              output_dir_path=output_dir_path, output_mp3_format=output_mp3_format,
              other_track_name=other_track_name).run()


if __name__ == '__main__':
    main()
