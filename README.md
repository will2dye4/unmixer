# unmixer - create and explore isolated tracks from music files

`unmixer` is a graphical utility and Python package for creating isolated tracks
(drums, bass, vocals, etc.) from music files.

## Installation

The easiest way to install the package is to download it from [PyPI](https://pypi.org) using `pip`.
Note that `unmixer` depends on [Python](https://www.python.org/downloads/) 3.11 or newer; please
ensure that you have a recent version of Python installed before proceeding.

Run the following command in a shell (a UNIX-like environment is assumed):

```
$ pip install unmixer
```

The package does depend on a few external Python packages available on PyPI. If you wish to
sandbox your installation inside a virtual environment, you may choose to use
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/) or a similar
utility to do so.

When successfully installed, a program called `unmixer` will be placed on your `PATH`. See the
Usage section below for details about how to use this program.

### Dependencies

* The utility expects [`ffmpeg`](https://ffmpeg.org) to be installed for mixing isolated
  tracks. See the project's [Downloads](https://ffmpeg.org/download.html) page for
  instructions on downloading and installing `ffmpeg`.

## Usage

The `unmixer` program is a graphical utility for exploring isolated tracks extracted
from a music file.

At any time, you can use the `-h` or `--help` flags to see a summary of options that
the program accepts.

```
$ unmixer -h
usage: unmixer [-h] [-o OUTPUT] [-g | -p] [music_file_or_track_dir]

create and explore isolated tracks from music files

positional arguments:
music_file_or_track_dir
path to the file to unmix, or path to a directory containing isolated tracks

options:
-h, --help            show this help message and exit
-o OUTPUT, --output OUTPUT, --output-dir OUTPUT
path to the directory for output isolated tracks (default: ~/unmixer)
-g, --guitar          Show "Guitar" track instead of "Other"
-p, --piano           Show "Piano" track instead of "Other"
```
