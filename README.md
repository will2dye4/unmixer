# unmixer - create and explore isolated tracks from music files

`unmixer` is a graphical utility and Python package for creating isolated tracks
(drums, bass, vocals, etc.) from music files.

`unmixer` is a frontend for [`demucs`](https://github.com/facebookresearch/demucs),
an excellent command-line utility for music source separation from the
[Meta Research](https://opensource.fb.com) team. The creation of isolated tracks
is handled entirely by `demucs`; `unmixer` provides a graphical interface for
viewing, playing, and exporting the isolated tracks in any combination.

## Installation

The easiest way to install the package is to download it from [PyPI](https://pypi.org) using `pip`.
Note that `unmixer` depends on [Python](https://www.python.org/downloads/) 3.11 or newer; please
ensure that you have a recent version of Python installed before proceeding.

Run the following command in a shell (Linux or macOS is assumed):

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
-g, --guitar          show "Guitar" track instead of "Other"
-p, --piano           show "Piano" track instead of "Other"
```

### Creating Isolated Tracks

To create isolated tracks for a specific song, pass the path to the song to `unmixer`.
For example:

```
$ unmixer /path/to/Limelight.mp3
```

When invoked with no arguments, `unmixer` will open a window containing a button
labeled `Choose...` (see the screenshot below).

![Song Selection Dialog](https://raw.githubusercontent.com/will2dye4/unmixer/master/images/song_selection_dialog.png)

Click the `Choose...` button and select a music file that you want to create
isolated tracks from. The interface will change to reflect that the song is
being processed (see the screenshot below).

![Song Processing Dialog](https://raw.githubusercontent.com/will2dye4/unmixer/master/images/song_processing_dialog.png)

**Please be patient during the process of creating the isolated tracks**, as it will
take some time to complete! It typically takes about as long as the source song itself
(or a bit longer) to create the isolated tracks for a song. For example, if a song
is 5 minutes long, it will likely take roughly 5 minutes to create isolated tracks for
that song.

**NOTE:** Although `unmixer` does not display a progress bar in its graphical interface
showing the status of processing the song, the progress will be shown in the process's
standard output (assuming the standard output is not redirected to a file). Check the
shell or terminal from which you launched the `unmixer` UI to get a better approximation
of how long it will take to process the song. A visual progress bar may be added in
a future version.

Although it may be possible to speed up the process by adjusting the flags passed to
`demucs`, the current implementation tends to favor producing higher quality isolated
tracks at the expense of taking a bit longer. A future version of `unmixer` may allow
customizing the quality, output format, machine learning model, or other settings that
can be configured by `demucs`; the current version does not allow any such customization.

#### Output Tracks

The following isolated tracks are created by default:

* `bass.wav`
* `drums.wav`
* `other.wav`
* `vocals.wav`

These are the sources that are supported by `demucs`; unfortunately, there is currently
no specific source available for guitar, piano, or any others besides bass, drums, and
vocals. Any part of the song's audio that is not identified as bass, drums, or vocals
will be found in the `other.wav` file.

#### Customizing the "Other" Track Name

In some cases, the isolated track `other.wav` may contain primarily a single instrument,
such as a guitar or piano. In these cases, it may be useful for the resulting output track
to have a corresponding name such as `guitar.wav` or `piano.wav` instead of the default
`other.wav`.

To change the name of the "other" track to `guitar.wav`, the `-g`/`--guitar` flag may be
passed to `unmixer`. Similarly, to change the name of the "other" track to `piano.wav`,
the `-p`/`--piano` flag may be passed to `unmixer` instead. (It is an error to pass both
`-g` and `-p` at the same time.) It is not currently possible to customize the name of the
"other" track to be any arbitrary name, although this feature may be added in a future version.

#### Output Directory

By default, `unmixer` creates isolated tracks in subdirectories of the directory `~/unmixer`.
Each song's isolated tracks will be placed in a new subdirectory of the output directory
named based on the song's filename. For example, isolated tracks for a song named
`Subdivisions.mp3` would be placed in the directory `~/unmixer/Subdivisions` by default
(note that the subdirectory does not include the `.mp3` file extension).

**NOTE:** Creating isolated tracks for multiple songs with the same filename will result in
any previous songs' isolated tracks being overwritten! If you need to process multiple distinct
songs with the same filename, be sure to rename the created directories (or rename the song
files themselves) to avoid conflicts!

Use the `-o`/`--output`/`--output-dir` flag to customize the output directory for isolated tracks
created by `unmixer`. A subdirectory of this directory will be created for the isolated tracks, as
described above.

### Exploring Isolated Tracks

To explore isolated tracks located in a specific directory, pass the path to the directory to
`unmixer`. For example:

```
$ unmixer ~/unmixer/YYZ
```

**NOTE:** If you used `unmixer` to create isolated tracks for a song, the Track Explorer window
will open automatically when the song is finished processing. (Again...please be patient!)

The Track Explorer window displays the name of the song at the top, a set of playback controls
at the bottom, and a waveform and a set of controls for each isolated track found in the input
directory (see the screenshot below).

![Track Explorer](https://raw.githubusercontent.com/will2dye4/unmixer/master/images/track_explorer.png)

#### Playback Controls

Use the `Play`/`Pause` button found in the playback controls at the bottom of the Track Explorer
to control playback of the currently selected track(s). Click the `Restart` button to start playback
at the beginning of the song.

When the song is playing, you can drag the triangular playhead (displayed above the very topmost
track, with a white line extending down over all of the waveforms) to skip to a specific part of
the song. Dragging the playhead while the song is paused is not currently supported.

#### Track Controls

Each track has its own `Mute` button and `Solo` button displayed to the left of the track's
waveform. Use a track's `Mute` button to remove that track from the mix you hear when playing
the song. Inversely, use a track's `Solo` button to hear **only** that track when playing
the song. As the name implies, only one track may have the `Solo` button active at a time.
A track may not be both soloed and muted at the same time; soloing a muted track will unmute
the track automatically. Playback will pause automatically if all tracks are muted at the
same time.

![Track Controls](https://raw.githubusercontent.com/will2dye4/unmixer/master/images/track_controls.png)

#### Exporting a Custom Mix

Use the `Export...` button found in the playback controls at the bottom of the Track Explorer
to export the currently selected (i.e., unmuted) tracks as a new file. A dialog box will open,
allowing you to select a destination for the file and click `Save`. For example, to create an
instrumental mix of a song, mute the `Vocals` track and export the remaining tracks as a new mix.

**NOTE:** Exporting is disabled when only a single track is selected, since that single track
is already a self-contained file that does not need to be re-exported. Similarly, exporting is
also disabled when all tracks are selected, since the resulting mix is the same as the original
song file that produced the isolated tracks in the first place.

If you export custom mixes in the same directory where the isolated tracks are located, the
custom mixes will also be loaded if you reopen the same directory using `unmixer` in the future.
If you want to avoid this, save any custom mixes to a different directory, such as a `remixes`
subdirectory of the directory where the isolated tracks are located.

#### Customizing the "Other" Track Name

In the same way as when creating isolated tracks (see above), the `-g`/`--guitar` flag may be
passed to `unmixer` to change the displayed name of the `Other` track (if present) to `Guitar`.
Similarly, to change the name of the `Other` track to `Piano`, the `-p`/`--piano` flag may be
passed to `unmixer` instead. (It is an error to pass both `-g` and `-p` at the same time.) It
is not currently possible to customize the name of the `Other` track to be any arbitrary name,
although this feature may be added in a future version.
