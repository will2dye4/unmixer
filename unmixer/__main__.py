#!/usr/bin/env python

from typing import Optional
import argparse
import os
import os.path
import sys

from unmixer.ui import UnmixerUI
from unmixer.util import expand_path, is_isolated_track


def parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='create and explore isolated tracks from music files')
    parser.add_argument('music_file_or_track_dir', nargs='?',
                        help='path to the file to unmix, or path to a directory containing isolated tracks')
    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> None:
    if args is None:
        args = sys.argv[1:]
    
    config = parse_args(args)
    input_dir_path = None
    song_path = None
    
    if path := config.music_file_or_track_dir:
        path = expand_path(path)
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
    
    print('Launching Unmixer UI...')
    UnmixerUI(song_path=song_path, input_dir_path=input_dir_path).run()


if __name__ == '__main__':
    main()
