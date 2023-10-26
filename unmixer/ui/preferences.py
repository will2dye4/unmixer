from dataclasses import dataclass
from typing import Any, Optional
import multiprocessing
import os.path

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from unmixer.constants import (
    ALLOWED_CLIP_MODES,
    ALLOWED_MP3_BITRATES_KBPS,
    ALLOWED_OTHER_TRACK_NAMES,
    ALLOWED_WAV_BIT_DEPTHS,
    DEFAULT_CLIP_MODE,
    DEFAULT_CPU_PARALLELISM,
    DEFAULT_CREATE_MODEL_SUBDIR,
    DEFAULT_DISABLE_GPU_ACCELERATION,
    DEFAULT_ISOLATED_TRACK_FORMAT,
    DEFAULT_MAX_SEGMENT_LENGTH_SECONDS,
    DEFAULT_MP3_BITRATE_KBPS,
    DEFAULT_MP3_PRESET,
    DEFAULT_OTHER_TRACK_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRETRAINED_MODEL,
    DEFAULT_SEGMENT_LENGTH_SECONDS,
    DEFAULT_SEGMENT_OVERLAP_PERCENT,
    DEFAULT_SHIFT_COUNT,
    DEFAULT_SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED,
    DEFAULT_SPLIT_INPUT_INTO_SEGMENTS,
    DEFAULT_WAV_DEPTH,
    ISOLATED_TRACK_FORMATS,
    MAX_SEGMENT_OVERLAP_PERCENT,
    MAX_SHIFT_COUNT,
    MIN_CPU_PARALLELISM,
    MIN_SEGMENT_LENGTH_SECONDS,
    MIN_SEGMENT_OVERLAP_PERCENT,
    MIN_SHIFT_COUNT,
    MP3_FORMAT,
    MP3_PRESET_MAX,
    MP3_PRESET_MIN,
    SHORT_MAX_SEGMENT_LENGTH_SECONDS,
    WAV_FORMAT,
    models,
    settings,
)
from unmixer.ui.constants import (
    FONT_WEIGHT_BOLD,
    OK_BUTTON_TEXT,
    OTHER_TRACK_NAME_DISABLED_TOOLTIP,
)
from unmixer.util import expand_path, get_available_pretrained_models, has_gpu_acceleration


# TODO - Add support for the following options:
# --repo REPO  (folder containing all pre-trained models for use with --name)
# --sig SIG  (locally trained XP signature)
# --filename FILENAME  Use "{track}", "{trackext}", "{stem}", "{ext}" to use variables of track name without extension,
#                      track extension, stem name and default output file extension. Default is "{track}/{stem}.{ext}".


@dataclass
class PretrainedModel:
    description: str
    max_segment_length_seconds: Optional[int] = None


# Reference: https://github.com/facebookresearch/demucs/blob/main/README.md#separating-tracks
PRETRAINED_MODELS = {
    models.HDEMUCS_MMI: PretrainedModel(
        description='Hybrid Demucs v3, retrained on MusDB + 800 songs.'
    ),
    models.HTDEMUCS: PretrainedModel(
        description='First version of Hybrid Transformer Demucs. Trained on MusDB + 800 songs.',
        max_segment_length_seconds=SHORT_MAX_SEGMENT_LENGTH_SECONDS,
    ),
    models.HTDEMUCS_6S: PretrainedModel(
        description='Six sources version of htdemucs, with piano and guitar being added as sources. '
                    'Note that the piano source is not working great at the moment.',
        max_segment_length_seconds=SHORT_MAX_SEGMENT_LENGTH_SECONDS,
    ),
    models.HTDEMUCS_FT: PretrainedModel(
        description='Fine-tuned version of htdemucs. Separation will take 4x longer but might be a bit better. '
                    'Same training set as htdemucs.',
        max_segment_length_seconds=SHORT_MAX_SEGMENT_LENGTH_SECONDS,
    ),
    models.MDX: PretrainedModel(
        description='Trained only on MusDB HQ. Winning model on track A at the MDX challenge.'
    ),
    models.MDX_EXTRA: PretrainedModel(
        description='Trained with extra training data, including MusDB test set. '
                    'Ranked 2nd on track B at the MDX challenge.'
    ),
    models.MDX_EXTRA_Q: PretrainedModel(
        description='Quantized version of mdx_extra. Smaller model size, but quality can be slightly worse.'
    ),
    models.MDX_Q: PretrainedModel(
        description='Quantized version of mdx. Smaller model size, but quality can be slightly worse.'
    ),
}

WAV_BIT_DEPTHS = {
    # e.g., 'int16' --> '16-bit (fixed point)'
    '{depth}-bit ({type} point)'.format(
        depth=allowed_depth.lstrip('abcdefghijklmnopqrstuvwxyz'),
        type=('fixed' if allowed_depth.rstrip('0123456789') == 'int' else 'floating')
    ): allowed_depth
    for allowed_depth in ALLOWED_WAV_BIT_DEPTHS
}


class DirectorySelector(QWidget):
    
    changed = pyqtSignal(str)
    
    BUTTON_TEXT = '📂'
    BUTTON_TOOLTIP = 'Choose a different directory'
    
    DEFAULT_FILE_DIALOG_TITLE = 'Select a Directory'
    
    # (left, top, right, bottom)
    NO_MARGIN = (0, 0, 0, 0)

    def __init__(self, dir_path: str, file_dialog_title: str = DEFAULT_FILE_DIALOG_TITLE) -> None:
        super().__init__()
        self.dir_path = expand_path(dir_path)
        self.file_dialog_title = file_dialog_title
        
        self.label = QLabel(self.dir_path)
        self.label.setContentsMargins(*self.NO_MARGIN)
        
        self.button = QPushButton(self.BUTTON_TEXT)
        self.button.setContentsMargins(*self.NO_MARGIN)
        self.button.setToolTip(self.BUTTON_TOOLTIP)
        self.button.clicked.connect(self.select_directory)
        
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        layout.setContentsMargins(*self.NO_MARGIN)
        self.setContentsMargins(*self.NO_MARGIN)
        self.setLayout(layout)
        self.show()
    
    def select_directory(self) -> None:
        input_path = QFileDialog.getExistingDirectory(self.parent(), self.file_dialog_title,
                                                      self.dir_path, QFileDialog.Option.ShowDirsOnly)
        
        if not input_path:
            return
        
        self.set_dir_path(input_path)
        self.changed.emit(self.dir_path)
        self.update()

    def set_dir_path(self, dir_path: str) -> None:
        self.dir_path = dir_path
        self.label.setText(self.dir_path)


class UnmixerPreferences(QWidget):

    ADVANCED_SECTION_HEADING = 'Advanced Settings'
    ISOLATED_TRACK_IMPORT_SECTION_HEADING = 'Isolated Track Import'
    PREDICTION_SECTION_HEADING = 'Prediction Parameters'
    
    AUDIO_FORMAT_LABEL = 'Output format'
    AUDIO_FORMAT_STATUS_TIP = 'Select the encoding for output isolated track files.'
    
    CLIP_MODE_LABEL = 'Clip mode'
    CLIP_MODE_STATUS_TIP = (
        'Select the strategy to avoid clipping: hard clamping or '
        'rescaling the entire signal (if necessary).'
    )

    CPU_PARALLELISM_LABEL = 'Parallelism'
    CPU_PARALLELISM_STATUS_TIP = (
        'Set the number of parallel workers to create for prediction. '
        'NOTE: Memory usage will increase in proportion to the number of workers!'
    )
    CPU_PARALLELISM_UNIT_LABEL = 'workers'

    CREATE_MODEL_SUBDIR_LABEL = 'Create subdirectory for model'
    CREATE_MODEL_SUBDIR_STATUS_TIP = (
        'If enabled, isolated tracks will be created in a subdirectory of the '
        'selected output directory named for the selected model.'
    )

    DISABLE_GPU_ACCELERATION_LABEL = 'Disable GPU acceleration'
    DISABLE_GPU_ACCELERATION_STATUS_TIP = 'Disable this setting if you encounter problems creating isolated tracks.'

    MP3_BITRATE_LABEL = 'MP3 bitrate'
    MP3_BITRATE_STATUS_TIP = (
        'Select the bitrate for encoding isolated track MP3 files. '
        'A higher bitrate means better quality but also larger files.'
    )
    MP3_BITRATE_UNIT_LABEL = 'kbps'
    
    BETTER_QUALITY_LABEL = 'Better Quality'
    FASTER_ENCODING_LABEL = 'Faster Encoding'
    MP3_PRESET_LABEL = 'MP3 preset'
    MP3_PRESET_STATUS_TIP = 'Select the preset for encoding isolated track MP3 files.'
    
    OPEN_TRACK_EXPLORER_LABEL = 'Open Track Explorer when finished'
    OPEN_TRACK_EXPLORER_STATUS_TIP = (
        'If enabled, a new Track Explorer window will open '
        'automatically when a song is finished processing.'
    )
    
    OTHER_TRACK_LABEL = '"Other" track name'
    OTHER_TRACK_STATUS_TIP = 'Select the name for the "Other" isolated track file.'
    
    OUTPUT_DIRECTORY_LABEL = 'Output directory'
    OUTPUT_DIRECTORY_FILE_DIALOG_TITLE = 'Select Output Directory'
    OUTPUT_DIRECTORY_STATUS_TIP = 'Select the directory where isolated track files will be written.'
    
    PRETRAINED_MODEL_LABEL = 'Pre-trained model'
    PRETRAINED_MODEL_STATUS_TIP = 'Select a pre-trained model to use for prediction.'

    SEGMENT_LENGTH_LABEL = 'Segment length'
    DEFAULT_SEGMENT_LENGTH_STATUS_TIP = (
        f'Set the length of each segment (in seconds). Allowed range is {MIN_SEGMENT_LENGTH_SECONDS} '
        f'to {DEFAULT_MAX_SEGMENT_LENGTH_SECONDS}.'
    )
    SHORT_SEGMENT_LENGTH_STATUS_TIP_TEMPLATE = (
        f'Set the length of each segment (in seconds). Allowed range for the selected model is '
        f'{MIN_SEGMENT_LENGTH_SECONDS} to {{max_segment_length_seconds}}.'
    )
    SEGMENT_LENGTH_UNITS_LABEL = 'seconds'

    SEGMENT_OVERLAP_LABEL = 'Segment overlap'
    SEGMENT_OVERLAP_STATUS_TIP = (
        'Set the percentage of overlap between segments. '
        f'Allowed range is {MIN_SEGMENT_OVERLAP_PERCENT} to {MAX_SEGMENT_OVERLAP_PERCENT}.'
    )
    SEGMENT_OVERLAP_UNITS_LABEL = '%'

    SHIFT_LABEL = 'Random shift count'
    SHIFT_STATUS_TIP = (
        'Set the number of random shifts to perform for each segment. '
        'NOTE: This will make prediction slower, proportional to the shift count!'
    )

    SPLIT_INTO_SEGMENTS_LABEL = 'Split song into segments for processing'
    SPLIT_INTO_SEGMENTS_STATUS_TIP = (
        'If enabled, input songs will be split into segments '
        'for prediction to reduce memory usage.'
    )
    SPLIT_INTO_SEGMENTS_DISABLED_TOOLTIP = OTHER_TRACK_NAME_DISABLED_TOOLTIP

    WAV_BIT_DEPTH_LABEL = 'WAV bit depth'
    WAV_BIT_DEPTH_STATUS_TIP = (
        'Select the bit depth for encoding isolated track WAV files. '
        'A higher bit depth means better quality but also larger files.'
    )

    RESTORE_DEFAULTS_BUTTON_TEXT = 'Restore Defaults'

    HEADING_FONT_SIZE = 18
    
    EFFECTIVE_MODEL_SUBDIR_LABEL_SPACING = 10
    LABEL_SPACING = 20
    ROW_SPACING = 15
    
    # (left, top, right, bottom)
    NO_MARGIN = (0, 0, 0, 0)
    SLIDER_LAYOUT_MARGIN = (0, 7, 0, 0)
    
    BUTTON_WIDTH = 150

    def __init__(self, parent: QWidget, app: 'UnmixerUI') -> None:
        super().__init__(parent)
        self.app = app
        
        # NOTE: Need to initialize this before self.create_model_subdir_checkbox!
        self.pretrained_model_combo_box = QComboBox()
        selected_model = self.setting(settings.prefs.PRETRAINED_MODEL)
        selected_model_info = None
        selected_index = 0
        for i, model in enumerate(get_available_pretrained_models()):
            display_name = model
            if model == DEFAULT_PRETRAINED_MODEL:
                display_name += ' (default)'
            self.pretrained_model_combo_box.addItem(display_name, model)
            if model_info := PRETRAINED_MODELS.get(model):
                self.pretrained_model_combo_box.setItemData(i, model_info.description,
                                                            Qt.ItemDataRole.StatusTipRole)
                self.pretrained_model_combo_box.setItemData(i, model_info.description,
                                                            Qt.ItemDataRole.ToolTipRole)
            if model == selected_model:
                selected_model_info = model_info
                selected_index = i
        self.pretrained_model_combo_box.setCurrentIndex(selected_index)
        self.pretrained_model_combo_box.currentIndexChanged.connect(self.update_pretrained_model)
        
        self.output_dir = DirectorySelector(self.app.output_dir_path,
                                            file_dialog_title=self.OUTPUT_DIRECTORY_FILE_DIALOG_TITLE)
        self.output_dir.changed.connect(self.output_dir_changed)

        self.create_model_subdir_checkbox = QCheckBox()
        self.create_model_subdir_checkbox.setChecked(self.setting(settings.importer.CREATE_MODEL_SUBDIR))
        self.create_model_subdir_checkbox.toggled.connect(self.create_model_subdir_setting_toggled)

        self.effective_output_dir_label = QLabel(self.effective_output_dir())
        self.create_model_subdir_layout = QHBoxLayout()
        self.create_model_subdir_layout.setContentsMargins(*self.NO_MARGIN)
        self.create_model_subdir_layout.addWidget(self.create_model_subdir_checkbox)
        self.create_model_subdir_layout.addSpacing(self.EFFECTIVE_MODEL_SUBDIR_LABEL_SPACING)
        self.create_model_subdir_layout.addWidget(self.effective_output_dir_label)

        self.audio_format_button_group = QButtonGroup()
        self.audio_format_button_group.setExclusive(True)
        self.audio_format_button_group.buttonToggled.connect(self.update_audio_format)
        
        self.audio_format_button_layout = QHBoxLayout()
        for audio_format in sorted(list(ISOLATED_TRACK_FORMATS)):
            format_button = QRadioButton(audio_format.upper())
            if audio_format == self.app.output_format:
                format_button.setChecked(True)
            self.audio_format_button_layout.addWidget(format_button)
            self.audio_format_button_group.addButton(format_button)
        
        self.other_track_button_group = QButtonGroup()
        self.other_track_button_group.setExclusive(True)
        self.other_track_button_group.buttonToggled.connect(self.update_other_track_name)

        self.other_track_button_layout = QHBoxLayout()
        disable_other_track_buttons = self.app.should_disable_other_track_name_selection()
        for other_name in ALLOWED_OTHER_TRACK_NAMES:
            name_button = QRadioButton(other_name.capitalize())
            if other_name == self.app.other_track_name:
                name_button.setChecked(True)
            if disable_other_track_buttons:
                name_button.setDisabled(True)
                name_button.setToolTip(OTHER_TRACK_NAME_DISABLED_TOOLTIP)
            self.other_track_button_layout.addWidget(name_button)
            self.other_track_button_group.addButton(name_button)
        
        self.open_track_explorer_checkbox = QCheckBox()
        self.open_track_explorer_checkbox.setChecked(
            self.setting(settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED)
        )
        self.open_track_explorer_checkbox.toggled.connect(self.open_track_explorer_setting_toggled)

        max_segment_length_seconds = DEFAULT_MAX_SEGMENT_LENGTH_SECONDS
        if selected_model_info and selected_model_info.max_segment_length_seconds:
            max_segment_length_seconds = selected_model_info.max_segment_length_seconds

        split_into_segments = self.setting(settings.prefs.SPLIT_INTO_SEGMENTS)
        if max_segment_length_seconds == SHORT_MAX_SEGMENT_LENGTH_SECONDS and not split_into_segments:
            split_into_segments = True
            self.update_setting(settings.prefs.SPLIT_INTO_SEGMENTS, split_into_segments)

        self.split_into_segments_checkbox = QCheckBox()
        self.split_into_segments_checkbox.setChecked(split_into_segments)
        self.split_into_segments_checkbox.setDisabled(max_segment_length_seconds == SHORT_MAX_SEGMENT_LENGTH_SECONDS)
        if not self.split_into_segments_checkbox.isEnabled():
            self.split_into_segments_checkbox.setToolTip(self.SPLIT_INTO_SEGMENTS_DISABLED_TOOLTIP)
        self.split_into_segments_checkbox.toggled.connect(self.split_into_segments_toggled)

        self.segment_length_label = None

        segment_length_seconds = self.setting(settings.prefs.SEGMENT_LENGTH)
        if segment_length_seconds > max_segment_length_seconds:
            segment_length_seconds = max_segment_length_seconds
            self.app.update_setting(settings.prefs.SEGMENT_LENGTH, max_segment_length_seconds)

        self.segment_length_spin_box = QSpinBox()
        self.segment_length_spin_box.setMinimum(MIN_SEGMENT_LENGTH_SECONDS)
        self.segment_length_spin_box.setMaximum(max_segment_length_seconds)
        self.segment_length_spin_box.setValue(segment_length_seconds)
        self.segment_length_spin_box.valueChanged.connect(self.update_segment_length)

        self.segment_length_layout = QHBoxLayout()
        self.segment_length_layout.setContentsMargins(*self.NO_MARGIN)
        self.segment_length_layout.addWidget(self.segment_length_spin_box)
        self.segment_length_layout.addWidget(QLabel(self.SEGMENT_LENGTH_UNITS_LABEL))

        self.segment_overlap_spin_box = QSpinBox()
        self.segment_overlap_spin_box.setMinimum(MIN_SEGMENT_OVERLAP_PERCENT)
        self.segment_overlap_spin_box.setMaximum(MAX_SEGMENT_OVERLAP_PERCENT)
        self.segment_overlap_spin_box.setValue(self.setting(settings.prefs.SEGMENT_OVERLAP))
        self.segment_overlap_spin_box.valueChanged.connect(self.update_segment_overlap)

        self.segment_overlap_layout = QHBoxLayout()
        self.segment_overlap_layout.setContentsMargins(*self.NO_MARGIN)
        self.segment_overlap_layout.addWidget(self.segment_overlap_spin_box)
        self.segment_overlap_layout.addWidget(QLabel(self.SEGMENT_OVERLAP_UNITS_LABEL))

        self.shift_count_spin_box = QSpinBox()
        self.shift_count_spin_box.setMinimum(MIN_SHIFT_COUNT)
        self.shift_count_spin_box.setMaximum(MAX_SHIFT_COUNT)
        self.shift_count_spin_box.setValue(self.setting(settings.prefs.SHIFT_COUNT))
        self.shift_count_spin_box.valueChanged.connect(self.update_shift_count)

        self.mp3_preset_slider = QSlider(Qt.Orientation.Horizontal)
        self.mp3_preset_slider.setMinimum(MP3_PRESET_MIN)
        self.mp3_preset_slider.setMaximum(MP3_PRESET_MAX)
        self.mp3_preset_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.mp3_preset_slider.setTickInterval(1)
        self.mp3_preset_slider.setValue(self.setting(settings.prefs.MP3_PRESET))
        self.mp3_preset_slider.valueChanged.connect(self.update_mp3_preset)
        
        self.mp3_preset_slider_layout = QHBoxLayout()
        self.mp3_preset_slider_layout.setContentsMargins(*self.SLIDER_LAYOUT_MARGIN)
        better_quality_label = QLabel(self.BETTER_QUALITY_LABEL)
        better_quality_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mp3_preset_slider_layout.addWidget(better_quality_label)
        self.mp3_preset_slider_layout.addWidget(self.mp3_preset_slider)
        faster_encoding_label = QLabel(self.FASTER_ENCODING_LABEL)
        faster_encoding_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.mp3_preset_slider_layout.addWidget(faster_encoding_label)
        
        self.mp3_bitrate_combo_box = QComboBox()
        self.mp3_bitrate_combo_box.setContentsMargins(*self.NO_MARGIN)
        selected_bitrate = self.setting(settings.prefs.MP3_BITRATE)
        selected_index = 0
        for i, bitrate in enumerate(ALLOWED_MP3_BITRATES_KBPS):
            self.mp3_bitrate_combo_box.addItem(str(bitrate))
            if bitrate == selected_bitrate:
                selected_index = i
        self.mp3_bitrate_combo_box.setCurrentIndex(selected_index)
        self.mp3_bitrate_combo_box.currentIndexChanged.connect(self.update_mp3_bitrate)
        
        self.mp3_bitrate_combo_box_layout = QHBoxLayout()
        self.mp3_bitrate_combo_box_layout.setContentsMargins(*self.NO_MARGIN)
        self.mp3_bitrate_combo_box_layout.addWidget(self.mp3_bitrate_combo_box)
        self.mp3_bitrate_combo_box_layout.addWidget(QLabel(self.MP3_BITRATE_UNIT_LABEL))
        
        self.wav_bit_depth_button_group = QButtonGroup()
        self.wav_bit_depth_button_group.setExclusive(True)
        self.wav_bit_depth_button_group.buttonToggled.connect(self.update_wav_bit_depth)

        self.wav_bit_depth_button_layout = QVBoxLayout()
        selected_bit_depth = self.setting(settings.prefs.WAV_BIT_DEPTH)
        for name, value in WAV_BIT_DEPTHS.items():
            depth_button = QRadioButton(name)
            if value == selected_bit_depth:
                depth_button.setChecked(True)
            self.wav_bit_depth_button_layout.addWidget(depth_button)
            self.wav_bit_depth_button_group.addButton(depth_button)
        
        self.clip_mode_button_group = QButtonGroup()
        self.clip_mode_button_group.setExclusive(True)
        self.clip_mode_button_group.buttonToggled.connect(self.update_clip_mode)

        self.clip_mode_button_layout = QHBoxLayout()
        selected_clip_mode = self.setting(settings.prefs.CLIP_MODE)
        for clip_mode in ALLOWED_CLIP_MODES:
            mode_button = QRadioButton(clip_mode.capitalize())
            if clip_mode == selected_clip_mode:
                mode_button.setChecked(True)
            self.clip_mode_button_layout.addWidget(mode_button)
            self.clip_mode_button_group.addButton(mode_button)

        self.disable_gpu_acceleration_checkbox = None
        if has_gpu_acceleration():
            self.disable_gpu_acceleration_checkbox = QCheckBox()
            self.disable_gpu_acceleration_checkbox.setChecked(self.setting(settings.prefs.DISABLE_GPU_ACCELERATION))
            self.disable_gpu_acceleration_checkbox.toggled.connect(self.disable_gpu_acceleration_toggled)

        self.cpu_parallelism_spin_box = None
        self.cpu_parallelism_layout = None
        self.cpu_count = multiprocessing.cpu_count()
        if self.cpu_count > 1:
            self.cpu_parallelism_spin_box = QSpinBox()
            self.cpu_parallelism_spin_box.setMinimum(MIN_CPU_PARALLELISM)
            self.cpu_parallelism_spin_box.setMaximum(self.cpu_count)
            self.cpu_parallelism_spin_box.setValue(self.setting(settings.prefs.CPU_PARALLELISM))
            self.cpu_parallelism_spin_box.valueChanged.connect(self.update_cpu_parallelism)

            self.cpu_parallelism_layout = QHBoxLayout()
            self.cpu_parallelism_layout.setContentsMargins(*self.NO_MARGIN)
            self.cpu_parallelism_layout.addWidget(self.cpu_parallelism_spin_box)
            self.cpu_parallelism_layout.addWidget(QLabel(self.CPU_PARALLELISM_UNIT_LABEL))

        self.restore_defaults_button = QPushButton(self.RESTORE_DEFAULTS_BUTTON_TEXT)
        self.restore_defaults_button.setFixedWidth(self.BUTTON_WIDTH)
        self.restore_defaults_button.clicked.connect(self.restore_defaults)

        self.ok_button = QPushButton(OK_BUTTON_TEXT)
        self.ok_button.setAutoDefault(True)
        self.ok_button.setDefault(True)
        self.ok_button.setFixedWidth(self.BUTTON_WIDTH)
        self.ok_button.clicked.connect(self.parent().close)
        
        self.form_layout = QFormLayout()
        self.create_form_layout()
        
        layout = QVBoxLayout()
        layout.addLayout(self.form_layout)
        sublayout = QHBoxLayout()
        sublayout.setAlignment(Qt.AlignmentFlag.AlignRight)
        sublayout.addWidget(self.restore_defaults_button)
        sublayout.addWidget(self.ok_button)
        layout.addLayout(sublayout)
        self.setLayout(layout)
        self.show()
    
    @property
    def selected_model(self) -> str:
        return self.pretrained_model_combo_box.itemData(self.pretrained_model_combo_box.currentIndex(),
                                                        Qt.ItemDataRole.UserRole)

    @property
    def max_segment_length_seconds(self) -> int:
        if (model_info := PRETRAINED_MODELS.get(self.selected_model)) and model_info.max_segment_length_seconds:
            return model_info.max_segment_length_seconds
        return DEFAULT_MAX_SEGMENT_LENGTH_SECONDS

    @staticmethod
    def form_field_label(text: str, status_tip: str) -> QLabel:
        label = QLabel(text)
        label.setStatusTip(status_tip)
        font = label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        label.setFont(font)
        return label

    def setting(self, key: str) -> Any:
        return self.app.setting(key)

    def update_setting(self, key: str, value: Any) -> None:
        self.app.update_setting(key, value)

    def create_form_layout(self) -> None:
        self.form_layout.setContentsMargins(*self.NO_MARGIN)
        self.form_layout.setHorizontalSpacing(self.LABEL_SPACING)
        self.form_layout.setVerticalSpacing(self.ROW_SPACING)
        
        # Isolated Track Import
        # ---------------------
        self.add_section_heading(self.ISOLATED_TRACK_IMPORT_SECTION_HEADING, include_top_padding=False)

        # Output Directory
        output_dir_label = self.form_field_label(self.OUTPUT_DIRECTORY_LABEL, self.OUTPUT_DIRECTORY_STATUS_TIP)
        self.form_layout.addRow(output_dir_label, self.output_dir)
        
        # Create subdirectory for model
        create_model_subdir_label = self.form_field_label(self.CREATE_MODEL_SUBDIR_LABEL,
                                                          self.CREATE_MODEL_SUBDIR_STATUS_TIP)
        self.form_layout.addRow(create_model_subdir_label, self.create_model_subdir_layout)

        # Output Format
        audio_format_label = self.form_field_label(self.AUDIO_FORMAT_LABEL, self.AUDIO_FORMAT_STATUS_TIP)
        self.form_layout.addRow(audio_format_label, self.audio_format_button_layout)
        
        # "Other" Track Name
        other_track_label = self.form_field_label(self.OTHER_TRACK_LABEL, self.OTHER_TRACK_STATUS_TIP)
        self.form_layout.addRow(other_track_label, self.other_track_button_layout)
        
        # Open Track Explorer when finished
        open_track_explorer_label = self.form_field_label(self.OPEN_TRACK_EXPLORER_LABEL,
                                                          self.OPEN_TRACK_EXPLORER_STATUS_TIP)
        self.form_layout.addRow(open_track_explorer_label, self.open_track_explorer_checkbox)
        
        # Prediction Parameters
        # ---------------------
        self.add_section_heading(self.PREDICTION_SECTION_HEADING)

        # Pre-trained Model
        pretrained_model_label = self.form_field_label(self.PRETRAINED_MODEL_LABEL, self.PRETRAINED_MODEL_STATUS_TIP)
        self.form_layout.addRow(pretrained_model_label, self.pretrained_model_combo_box)

        # Split song into segments for processing
        split_into_segments_label = self.form_field_label(self.SPLIT_INTO_SEGMENTS_LABEL,
                                                          self.SPLIT_INTO_SEGMENTS_STATUS_TIP)
        self.form_layout.addRow(split_into_segments_label, self.split_into_segments_checkbox)

        # Segment Length
        segment_length_status_tip = self.DEFAULT_SEGMENT_LENGTH_STATUS_TIP
        if (max_segment_length_seconds := self.max_segment_length_seconds) == SHORT_MAX_SEGMENT_LENGTH_SECONDS:
            segment_length_status_tip = self.SHORT_SEGMENT_LENGTH_STATUS_TIP_TEMPLATE.format(
                max_segment_length_seconds=max_segment_length_seconds
            )
        self.segment_length_label = self.form_field_label(self.SEGMENT_LENGTH_LABEL, segment_length_status_tip)
        self.form_layout.addRow(self.segment_length_label, self.segment_length_layout)
        self.form_layout.setRowVisible(self.segment_length_layout, self.split_into_segments_checkbox.isChecked())

        # Segment Overlap
        segment_overlap_label = self.form_field_label(self.SEGMENT_OVERLAP_LABEL, self.SEGMENT_OVERLAP_STATUS_TIP)
        self.form_layout.addRow(segment_overlap_label, self.segment_overlap_layout)
        self.form_layout.setRowVisible(self.segment_overlap_layout, self.split_into_segments_checkbox.isChecked())

        # Random Shift Count
        shift_count_label = self.form_field_label(self.SHIFT_LABEL, self.SHIFT_STATUS_TIP)
        self.form_layout.addRow(shift_count_label, self.shift_count_spin_box)
        self.form_layout.setRowVisible(self.shift_count_spin_box, self.split_into_segments_checkbox.isChecked())

        # Advanced Settings
        # -----------------
        self.add_section_heading(self.ADVANCED_SECTION_HEADING)
        
        # MP3 Preset
        mp3_preset_label = self.form_field_label(self.MP3_PRESET_LABEL, self.MP3_PRESET_STATUS_TIP)
        self.form_layout.addRow(mp3_preset_label, self.mp3_preset_slider_layout)

        # MP3 Bitrate
        mp3_bitrate_label = self.form_field_label(self.MP3_BITRATE_LABEL, self.MP3_BITRATE_STATUS_TIP)
        self.form_layout.addRow(mp3_bitrate_label, self.mp3_bitrate_combo_box_layout)

        # WAV Bit Depth
        wav_bit_depth_label = self.form_field_label(self.WAV_BIT_DEPTH_LABEL, self.WAV_BIT_DEPTH_STATUS_TIP)
        wav_bit_depth_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.form_layout.addRow(wav_bit_depth_label, self.wav_bit_depth_button_layout)

        if self.app.output_format != MP3_FORMAT:
            self.hide_mp3_preferences()
        if self.app.output_format != WAV_FORMAT:
            self.hide_wav_preferences()

        # Clip Mode
        clip_mode_label = self.form_field_label(self.CLIP_MODE_LABEL, self.CLIP_MODE_STATUS_TIP)
        self.form_layout.addRow(clip_mode_label, self.clip_mode_button_layout)

        # Disable GPU Acceleration - only shown if GPU acceleration is available to begin with
        if self.disable_gpu_acceleration_checkbox:
            disable_gpu_acceleration_label = self.form_field_label(self.DISABLE_GPU_ACCELERATION_LABEL,
                                                                   self.DISABLE_GPU_ACCELERATION_STATUS_TIP)
            self.form_layout.addRow(disable_gpu_acceleration_label, self.disable_gpu_acceleration_checkbox)

        # CPU Parallelism - only shown if system is multi-core
        if self.cpu_parallelism_layout:
            cpu_parallelism_label = self.form_field_label(self.CPU_PARALLELISM_LABEL, self.CPU_PARALLELISM_STATUS_TIP)
            self.form_layout.addRow(cpu_parallelism_label, self.cpu_parallelism_layout)
            self.form_layout.setRowVisible(self.cpu_parallelism_layout, self.should_show_cpu_parallelism_slider())
    
    def add_section_heading(self, heading: str, include_top_padding: bool = True) -> None:
        if include_top_padding:
            self.form_layout.addRow(QLabel(''))
        
        heading_label = QLabel(heading)
        font = heading_label.font()
        font.setPixelSize(self.HEADING_FONT_SIZE)
        font.setWeight(FONT_WEIGHT_BOLD)
        heading_label.setFont(font)
        self.form_layout.addRow(heading_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.form_layout.addRow(line)
    
    def effective_output_dir(self) -> str:
        if self.create_model_subdir_checkbox.isChecked():
            return str(os.path.join(self.app.output_dir_path, self.selected_model))
        return ''

    def should_show_cpu_parallelism_slider(self) -> bool:
        return self.cpu_count > 1 and (not has_gpu_acceleration() or
                                       self.disable_gpu_acceleration_checkbox.isChecked())

    def show_mp3_preferences(self) -> None:
        self.form_layout.setRowVisible(self.mp3_preset_slider_layout, True)
        self.form_layout.setRowVisible(self.mp3_bitrate_combo_box_layout, True)
    
    def hide_mp3_preferences(self) -> None:
        self.form_layout.setRowVisible(self.mp3_preset_slider_layout, False)
        self.form_layout.setRowVisible(self.mp3_bitrate_combo_box_layout, False)
    
    def show_wav_preferences(self) -> None:
        self.form_layout.setRowVisible(self.wav_bit_depth_button_layout, True)
    
    def hide_wav_preferences(self) -> None:
        self.form_layout.setRowVisible(self.wav_bit_depth_button_layout, False)
    
    def disable_other_track_name_buttons(self) -> None:
        for button in self.other_track_button_group.buttons():
            button.setDisabled(True)
            button.setToolTip(OTHER_TRACK_NAME_DISABLED_TOOLTIP)

    def enable_other_track_name_buttons(self) -> None:
        for button in self.other_track_button_group.buttons():
            button.setDisabled(False)
            button.setToolTip('')

    def refresh_output_format_preferences(self) -> None:
        if self.app.output_format == MP3_FORMAT:
            self.show_mp3_preferences()
        else:
            self.hide_mp3_preferences()
        
        if self.app.output_format == WAV_FORMAT:
            self.show_wav_preferences()
        else:
            self.hide_wav_preferences()
        
        self.update()
    
    def refresh_other_track_name_preferences(self) -> None:
        # htdemucs_6s has guitar and piano as sources, so disable setting the "other" track name to those.
        if self.app.should_disable_other_track_name_selection():
            if self.app.other_track_name != DEFAULT_OTHER_TRACK_NAME:
                self.app.other_track_name = DEFAULT_OTHER_TRACK_NAME
                self.set_other_track_name(self.app.other_track_name)
            self.disable_other_track_name_buttons()
            if self.app.import_window:
                self.app.import_window.set_other_track_name(self.app.other_track_name)
                self.app.import_window.importer.import_settings.disable_other_track_name_buttons()
        else:
            self.enable_other_track_name_buttons()
            if self.app.import_window:
                self.app.import_window.importer.import_settings.enable_other_track_name_buttons()

    def refresh_create_model_subdir_preference(self) -> None:
        self.effective_output_dir_label.setText(self.effective_output_dir())

    def refresh_segment_preferences(self) -> None:
        max_segment_length = self.max_segment_length_seconds
        if max_segment_length != self.segment_length_spin_box.maximum():
            self.segment_length_spin_box.setMaximum(max_segment_length)
            if self.segment_length_spin_box.value() > max_segment_length:
                self.segment_length_spin_box.setValue(max_segment_length)
                self.app.update_setting(settings.prefs.SEGMENT_LENGTH, max_segment_length)
        segment_length_status_tip = self.DEFAULT_SEGMENT_LENGTH_STATUS_TIP
        if max_segment_length == SHORT_MAX_SEGMENT_LENGTH_SECONDS:
            segment_length_status_tip = self.SHORT_SEGMENT_LENGTH_STATUS_TIP_TEMPLATE.format(
                max_segment_length_seconds=max_segment_length
            )
        self.segment_length_label.setStatusTip(segment_length_status_tip)

        if max_segment_length == SHORT_MAX_SEGMENT_LENGTH_SECONDS:
            if not self.split_into_segments_checkbox.isChecked():
                self.split_into_segments_checkbox.setChecked(True)
                self.update_setting(settings.prefs.SPLIT_INTO_SEGMENTS, True)
            self.split_into_segments_checkbox.setDisabled(True)
            self.split_into_segments_checkbox.setToolTip(self.SPLIT_INTO_SEGMENTS_DISABLED_TOOLTIP)
        else:
            self.split_into_segments_checkbox.setDisabled(False)
            self.split_into_segments_checkbox.setToolTip('')

    def restore_defaults(self) -> None:
        output_dir = expand_path(DEFAULT_OUTPUT_DIR)
        self.output_dir.set_dir_path(output_dir)
        self.output_dir_changed(output_dir)

        create_model_subdir = DEFAULT_CREATE_MODEL_SUBDIR
        self.create_model_subdir_checkbox.setChecked(create_model_subdir)
        self.update_setting(settings.importer.CREATE_MODEL_SUBDIR, create_model_subdir)

        audio_format = DEFAULT_ISOLATED_TRACK_FORMAT
        self.set_audio_format(audio_format)
        self.app.output_format = audio_format
        self.update_setting(settings.importer.AUDIO_FORMAT, audio_format)
        if self.app.import_window:
            self.app.import_window.set_audio_format(audio_format)

        other_track_name = DEFAULT_OTHER_TRACK_NAME
        self.set_other_track_name(other_track_name)
        self.app.other_track_name = other_track_name
        self.update_setting(settings.prefs.OTHER_TRACK_NAME, other_track_name)
        if self.app.import_window:
            self.app.import_window.set_other_track_name(other_track_name)

        show_track_explorer_window = DEFAULT_SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED
        self.open_track_explorer_checkbox.setChecked(show_track_explorer_window)
        self.update_setting(settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED, show_track_explorer_window)

        pretrained_model = DEFAULT_PRETRAINED_MODEL
        self.set_pretrained_model(pretrained_model)
        self.update_setting(settings.prefs.PRETRAINED_MODEL, pretrained_model)

        split_into_segments = DEFAULT_SPLIT_INPUT_INTO_SEGMENTS
        self.set_split_into_segments(split_into_segments)
        self.update_setting(settings.prefs.SPLIT_INTO_SEGMENTS, split_into_segments)

        segment_length = DEFAULT_SEGMENT_LENGTH_SECONDS
        self.segment_length_spin_box.setValue(segment_length)
        self.update_setting(settings.prefs.SEGMENT_LENGTH, segment_length)

        segment_overlap = DEFAULT_SEGMENT_OVERLAP_PERCENT
        self.segment_overlap_spin_box.setValue(segment_overlap)
        self.update_setting(settings.prefs.SEGMENT_OVERLAP, segment_overlap)

        shift_count = DEFAULT_SHIFT_COUNT
        self.shift_count_spin_box.setValue(shift_count)
        self.update_setting(settings.prefs.SHIFT_COUNT, shift_count)

        mp3_preset = DEFAULT_MP3_PRESET
        self.mp3_preset_slider.setValue(mp3_preset)
        self.update_setting(settings.prefs.MP3_PRESET, mp3_preset)

        mp3_bitrate = DEFAULT_MP3_BITRATE_KBPS
        self.set_mp3_bitrate(mp3_bitrate)
        self.update_setting(settings.prefs.MP3_BITRATE, mp3_bitrate)

        wav_bit_depth = DEFAULT_WAV_DEPTH
        self.set_wav_bit_depth(wav_bit_depth)
        self.update_setting(settings.prefs.WAV_BIT_DEPTH, wav_bit_depth)

        clip_mode = DEFAULT_CLIP_MODE
        self.set_clip_mode(clip_mode)
        self.update_setting(settings.prefs.CLIP_MODE, clip_mode)

        if self.disable_gpu_acceleration_checkbox:
            disable_gpu_acceleration = DEFAULT_DISABLE_GPU_ACCELERATION
            self.disable_gpu_acceleration_checkbox.setChecked(disable_gpu_acceleration)
            self.update_setting(settings.prefs.DISABLE_GPU_ACCELERATION, disable_gpu_acceleration)
            if self.cpu_parallelism_layout:
                self.form_layout.setRowVisible(self.cpu_parallelism_layout, self.should_show_cpu_parallelism_slider())

        if self.cpu_parallelism_layout:
            cpu_parallelism = DEFAULT_CPU_PARALLELISM
            self.cpu_parallelism_spin_box.setValue(cpu_parallelism)
            self.update_setting(settings.prefs.CPU_PARALLELISM, cpu_parallelism)

        self.refresh_create_model_subdir_preference()
        self.update()

    def create_model_subdir_setting_toggled(self) -> None:
        create_model_subdir = self.create_model_subdir_checkbox.isChecked()
        self.refresh_create_model_subdir_preference()
        self.update_setting(settings.importer.CREATE_MODEL_SUBDIR, create_model_subdir)

    def open_track_explorer_setting_toggled(self) -> None:
        show_track_explorer = self.open_track_explorer_checkbox.isChecked()
        self.update_setting(settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED, show_track_explorer)
    
    def output_dir_changed(self, new_output_dir_path: str) -> None:
        if new_output_dir_path != self.app.output_dir_path:
            self.update_setting(settings.importer.OUTPUT_DIR_PATH, new_output_dir_path)
            self.app.output_dir_path = new_output_dir_path
            self.refresh_create_model_subdir_preference()
    
    def set_audio_format(self, audio_format: str) -> None:
        audio_format = audio_format.lower()
        if audio_format not in ISOLATED_TRACK_FORMATS:
            raise ValueError(f'Unsupported audio format "{audio_format}"!')

        for button in self.audio_format_button_group.buttons():
            button.setChecked(button.text().lower() == audio_format)
        
        self.refresh_output_format_preferences()
    
    def update_audio_format(self, button: QRadioButton, checked: bool) -> None:
        if checked and (audio_format := button.text().lower()) != self.app.output_format:
            self.app.output_format = audio_format
            self.update_setting(settings.importer.AUDIO_FORMAT, audio_format)
            self.refresh_output_format_preferences()
            
            if self.app.import_window:
                self.app.import_window.set_audio_format(self.app.output_format)
    
    def set_other_track_name(self, other_track_name: str) -> None:
        other_track_name = other_track_name.lower()
        if other_track_name not in ALLOWED_OTHER_TRACK_NAMES:
            raise ValueError(f'Unsupported track name "{other_track_name}"!')

        for button in self.other_track_button_group.buttons():
            button.setChecked(button.text().lower() == other_track_name)

    def update_other_track_name(self, button: QRadioButton, checked: bool) -> None:
        if checked and (track_name := button.text().lower()) != self.app.other_track_name:
            self.app.other_track_name = track_name
            self.update_setting(settings.prefs.OTHER_TRACK_NAME, track_name)

            if self.app.import_window:
                self.app.import_window.set_other_track_name(self.app.other_track_name)
    
    def set_pretrained_model(self, new_model_name: str) -> None:
        for i in range(self.pretrained_model_combo_box.count()):
            model_name = self.pretrained_model_combo_box.itemData(i, Qt.ItemDataRole.UserRole)
            if model_name == new_model_name:
                self.pretrained_model_combo_box.setCurrentIndex(i)
                self.refresh_create_model_subdir_preference()
                self.refresh_other_track_name_preferences()
                self.refresh_segment_preferences()
                break

    def update_pretrained_model(self) -> None:
        self.update_setting(settings.prefs.PRETRAINED_MODEL, self.selected_model)
        self.refresh_create_model_subdir_preference()
        self.refresh_other_track_name_preferences()
        self.refresh_segment_preferences()

    def set_mp3_bitrate(self, new_bitrate: int) -> None:
        for i in range(self.mp3_bitrate_combo_box.count()):
            bitrate = int(self.mp3_bitrate_combo_box.itemText(i))
            if bitrate == new_bitrate:
                self.mp3_bitrate_combo_box.setCurrentIndex(i)
                break

    def update_mp3_bitrate(self) -> None:
        mp3_bitrate = int(self.mp3_bitrate_combo_box.currentText())
        self.update_setting(settings.prefs.MP3_BITRATE, mp3_bitrate)
    
    def update_mp3_preset(self) -> None:
        mp3_preset = max(MP3_PRESET_MIN, min(self.mp3_preset_slider.value(), MP3_PRESET_MAX))
        self.update_setting(settings.prefs.MP3_PRESET, mp3_preset)
    
    def set_wav_bit_depth(self, bit_depth: str) -> None:
        for button in self.wav_bit_depth_button_group.buttons():
            button.setChecked(WAV_BIT_DEPTHS[button.text()] == bit_depth)

    def set_clip_mode(self, clip_mode: str) -> None:
        for button in self.clip_mode_button_group.buttons():
            button.setChecked(button.text().lower() == clip_mode)

    def update_wav_bit_depth(self, button: QRadioButton, checked: bool) -> None:
        if checked:
            self.update_setting(settings.prefs.WAV_BIT_DEPTH, WAV_BIT_DEPTHS[button.text()])

    def update_clip_mode(self, button: QRadioButton, checked: bool) -> None:
        if checked:
            self.update_setting(settings.prefs.CLIP_MODE, button.text().lower())

    def update_cpu_parallelism(self) -> None:
        parallelism = max(MIN_CPU_PARALLELISM, min(self.cpu_parallelism_spin_box.value(), self.cpu_count))
        self.update_setting(settings.prefs.CPU_PARALLELISM, parallelism)

    def disable_gpu_acceleration_toggled(self) -> None:
        disable_gpu_acceleration = self.disable_gpu_acceleration_checkbox.isChecked()
        if self.cpu_parallelism_layout:
            self.form_layout.setRowVisible(self.cpu_parallelism_layout, self.should_show_cpu_parallelism_slider())
        self.update_setting(settings.prefs.DISABLE_GPU_ACCELERATION, disable_gpu_acceleration)

    def set_split_into_segments(self, split_into_segments: bool) -> None:
        self.split_into_segments_checkbox.setChecked(split_into_segments)
        self.form_layout.setRowVisible(self.segment_length_layout, split_into_segments)
        self.form_layout.setRowVisible(self.segment_overlap_layout, split_into_segments)
        self.form_layout.setRowVisible(self.shift_count_spin_box, split_into_segments)

    def split_into_segments_toggled(self) -> None:
        split_into_segments = self.split_into_segments_checkbox.isChecked()
        self.set_split_into_segments(split_into_segments)
        self.update_setting(settings.prefs.SPLIT_INTO_SEGMENTS, split_into_segments)

    def update_segment_length(self) -> None:
        segment_length = max(MIN_SEGMENT_LENGTH_SECONDS,
                             min(self.segment_length_spin_box.value(), self.max_segment_length_seconds))
        self.update_setting(settings.prefs.SEGMENT_LENGTH, segment_length)

    def update_segment_overlap(self) -> None:
        segment_overlap = max(MIN_SEGMENT_OVERLAP_PERCENT,
                              min(self.segment_overlap_spin_box.value(), MAX_SEGMENT_OVERLAP_PERCENT))
        self.update_setting(settings.prefs.SEGMENT_OVERLAP, segment_overlap)

    def update_shift_count(self) -> None:
        shift_count = max(MIN_SHIFT_COUNT, min(self.shift_count_spin_box.value(), MAX_SHIFT_COUNT))
        self.update_setting(settings.prefs.SHIFT_COUNT, shift_count)
