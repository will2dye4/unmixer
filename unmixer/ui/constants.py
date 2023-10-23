from types import SimpleNamespace


APP_NAME = 'Unmixer'
ORGANIZATION_NAME = 'DyeSoft'
PROJECT_README_URL = 'https://github.com/will2dye4/unmixer#usage'

ERROR_MESSAGE_TITLE = 'Error'
SUCCESS_MESSAGE_TITLE = 'Success'

OK_BUTTON_TEXT = 'OK'

FONT_WEIGHT_BOLD = 800

#################
# Settings Keys #
#################

settings = SimpleNamespace()

# -- Import Settings -- #
settings.importer = SimpleNamespace()
# The audio format used when importing songs (str).
settings.importer.AUDIO_FORMAT = 'import/audioFormat'
# The working directory for the file dialog presented when importing a song (str).
settings.importer.DIR_PATH = 'import/dirPath'
# The output directory for isolated tracks created when importing songs (str).
settings.importer.OUTPUT_DIR_PATH = 'import/outputDirPath'

# -- Open File/Directory Settings -- #
settings.open = SimpleNamespace()
# The most recently opened isolated track directories, used to populate the File > Recently Opened menu (list[str]).
settings.open.RECENTLY_OPENED = 'open/recentlyOpened'
# The working directory for the file dialog presented when opening existing isolated tracks (str).
settings.open.TRACK_DIR_PATH = 'open/trackDirPath'

# -- Playback Settings -- #
settings.playback = SimpleNamespace()
# The most recent playback volume (int).
settings.playback.VOLUME = 'playback/volume'

# -- User Preferences -- #
settings.prefs = SimpleNamespace()
# MP3 bitrate to use when MP3 format is selected (int). Value is in kbps.
settings.prefs.MP3_BITRATE = 'prefs/mp3BitRate'
# MP3 preset to use when MP3 format is selected (int). Range is 2 (better quality) to 7 (faster encoding).
settings.prefs.MP3_PRESET = 'prefs/mp3Preset'
# The name of the "other" track, used for importing songs and exploring isolated tracks (str).
settings.prefs.OTHER_TRACK_NAME = 'prefs/otherTrackName'
# Whether or not to show the Track Explorer window after importing a song (bool).
settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED = 'prefs/showTrackExplorer'
# Bit depth to use when WAV format is selected (str). Valid values are 'int16', 'int24', and 'float32'.
settings.prefs.WAV_BIT_DEPTH = 'prefs/wavBitDepth'
