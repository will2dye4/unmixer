from types import SimpleNamespace
import os

from demucs.pretrained import DEFAULT_MODEL


DEFAULT_OUTPUT_DIR = '~/unmixer'

GUITAR_TRACK_NAME = 'guitar'
OTHER_TRACK_NAME = 'other'
PIANO_TRACK_NAME = 'piano'
DEFAULT_OTHER_TRACK_NAME = OTHER_TRACK_NAME
ALLOWED_OTHER_TRACK_NAMES = (GUITAR_TRACK_NAME, PIANO_TRACK_NAME, OTHER_TRACK_NAME)  # in display order

FLAC_FORMAT = 'flac'
MP3_FORMAT = 'mp3'
WAV_FORMAT = 'wav'
DEFAULT_ISOLATED_TRACK_FORMAT = WAV_FORMAT
ISOLATED_TRACK_FORMATS = {FLAC_FORMAT, MP3_FORMAT, WAV_FORMAT}

MIN_VOLUME = 0
MAX_VOLUME = 100
DEFAULT_VOLUME = 80

MP3_PRESET_MIN = 2  # Better quality
MP3_PRESET_MAX = 7  # Faster encoding
DEFAULT_MP3_PRESET = MP3_PRESET_MIN

# Reference: https://en.wikipedia.org/wiki/MP3#Bit_rate
ALLOWED_MP3_BITRATES_KBPS = (96, 112, 128, 160, 192, 224, 256, 320)
DEFAULT_MP3_BITRATE_KBPS = 320

WAV_DEPTH_INT16 = 'int16'
WAV_DEPTH_INT24 = 'int24'
WAV_DEPTH_FLOAT32 = 'float32'
DEFAULT_WAV_DEPTH = WAV_DEPTH_INT16
ALLOWED_WAV_BIT_DEPTHS = (WAV_DEPTH_INT16, WAV_DEPTH_INT24, WAV_DEPTH_FLOAT32)  # in display order

HTDEMUCS_6S_MODEL_NAME = 'htdemucs_6s'
DEFAULT_PRETRAINED_MODELS = ('hdemucs_mmi', 'htdemucs', HTDEMUCS_6S_MODEL_NAME, 'htdemucs_ft', 'mdx', 'mdx_extra', 'mdx_q')

DEFAULT_CREATE_MODEL_SUBDIR = True
DEFAULT_DISABLE_GPU_ACCELERATION = False
DEFAULT_SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED = True
DEFAULT_SPLIT_INPUT_INTO_SEGMENTS = True

CLAMP_CLIP_MODE = 'clamp'
RESCALE_CLIP_MODE = 'rescale'
DEFAULT_CLIP_MODE = RESCALE_CLIP_MODE
ALLOWED_CLIP_MODES = (CLAMP_CLIP_MODE, DEFAULT_CLIP_MODE)

MIN_CPU_PARALLELISM = 1
DEFAULT_CPU_PARALLELISM = MIN_CPU_PARALLELISM

MIN_SEGMENT_LENGTH_SECONDS = 5
MAX_SEGMENT_LENGTH_SECONDS = 120
DEFAULT_SEGMENT_LENGTH_SECONDS = 10

MIN_SEGMENT_OVERLAP_PERCENT = 0
MAX_SEGMENT_OVERLAP_PERCENT = 50
DEFAULT_SEGMENT_OVERLAP_PERCENT = 25

MIN_SHIFT_COUNT = 0
MAX_SHIFT_COUNT = 10
DEFAULT_SHIFT_COUNT = MIN_SHIFT_COUNT

#################
# Settings Keys #
#################

settings = SimpleNamespace()

# -- Import Settings -- #
settings.importer = SimpleNamespace()
# The audio format used when importing songs (str).
settings.importer.AUDIO_FORMAT = 'import/audioFormat'
# Whether or not to create a subdirectory of OUTPUT_DIR_PATH named for the prediction model (bool).
settings.importer.CREATE_MODEL_SUBDIR = 'import/createModelSubdir'
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
# The strategy to use for avoiding clipping (str). Valid values are 'clamp' and 'rescale'.
settings.prefs.CLIP_MODE = 'prefs/clipMode'
# Number of parallel jobs to use when running on CPU (int).
settings.prefs.CPU_PARALLELISM = 'prefs/cpuParallelism'
# Whether or not to disable GPU acceleration (i.e., force running on CPU) for demucs (bool).
settings.prefs.DISABLE_GPU_ACCELERATION = 'prefs/disableGPUAcceleration'
# MP3 bitrate to use when MP3 format is selected (int). Value is in kbps.
settings.prefs.MP3_BITRATE = 'prefs/mp3BitRate'
# MP3 preset to use when MP3 format is selected (int). Range is 2 (better quality) to 7 (faster encoding).
settings.prefs.MP3_PRESET = 'prefs/mp3Preset'
# The name of the "other" track, used for importing songs and exploring isolated tracks (str).
settings.prefs.OTHER_TRACK_NAME = 'prefs/otherTrackName'
# The name of the pre-trained model to use for source separation (str).
settings.prefs.PRETRAINED_MODEL = 'prefs/pretrainedModel'
# Segment length when song is split into segments for processing (int). Value is in seconds.
settings.prefs.SEGMENT_LENGTH = 'prefs/segmentLength'
# Segment overlap when song is split into segments for processing (int). Value is a percentage (0-100).
settings.prefs.SEGMENT_OVERLAP = 'prefs/segmentOverlap'
# Number of random shifts to perform during prediction (int).
settings.prefs.SHIFT_COUNT = 'prefs/shiftCount'
# Whether or not to show the Track Explorer window after importing a song (bool).
settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED = 'prefs/showTrackExplorer'
# Whether or not to split input songs into segments for processing (bool).
settings.prefs.SPLIT_INTO_SEGMENTS = 'prefs/splitIntoSegments'
# Bit depth to use when WAV format is selected (str). Valid values are 'int16', 'int24', and 'float32'.
settings.prefs.WAV_BIT_DEPTH = 'prefs/wavBitDepth'


####################
# Default Settings #
####################

DEFAULT_SETTINGS = {
    settings.importer.AUDIO_FORMAT: DEFAULT_ISOLATED_TRACK_FORMAT,
    settings.importer.CREATE_MODEL_SUBDIR: DEFAULT_CREATE_MODEL_SUBDIR,
    settings.importer.DIR_PATH: os.getcwd(),
    settings.importer.OUTPUT_DIR_PATH: DEFAULT_OUTPUT_DIR,
    settings.open.RECENTLY_OPENED: [],
    settings.open.TRACK_DIR_PATH: None,  # Default is the current output dir path setting.
    settings.playback.VOLUME: DEFAULT_VOLUME,
    settings.prefs.CLIP_MODE: DEFAULT_CLIP_MODE,
    settings.prefs.CPU_PARALLELISM: DEFAULT_CPU_PARALLELISM,
    settings.prefs.DISABLE_GPU_ACCELERATION: DEFAULT_DISABLE_GPU_ACCELERATION,
    settings.prefs.MP3_BITRATE: DEFAULT_MP3_BITRATE_KBPS,
    settings.prefs.MP3_PRESET: DEFAULT_MP3_PRESET,
    settings.prefs.OTHER_TRACK_NAME: DEFAULT_OTHER_TRACK_NAME,
    settings.prefs.PRETRAINED_MODEL: DEFAULT_MODEL,
    settings.prefs.SEGMENT_LENGTH: DEFAULT_SEGMENT_LENGTH_SECONDS,
    settings.prefs.SEGMENT_OVERLAP: DEFAULT_SEGMENT_OVERLAP_PERCENT,
    settings.prefs.SHIFT_COUNT: DEFAULT_SHIFT_COUNT,
    settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED: DEFAULT_SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED,
    settings.prefs.SPLIT_INTO_SEGMENTS: DEFAULT_SPLIT_INPUT_INTO_SEGMENTS,
    settings.prefs.WAV_BIT_DEPTH: DEFAULT_WAV_DEPTH,
}
