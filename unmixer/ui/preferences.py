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
    QVBoxLayout,
    QWidget,
)

from unmixer.constants import (
    ALLOWED_MP3_BITRATES_KBPS,
    ALLOWED_OTHER_TRACK_NAMES,
    ALLOWED_WAV_BIT_DEPTHS,
    DEFAULT_MP3_BITRATE_KBPS,
    DEFAULT_MP3_PRESET,
    DEFAULT_WAV_DEPTH,
    ISOLATED_TRACK_FORMATS,
    MP3_FORMAT,
    MP3_PRESET_MAX,
    MP3_PRESET_MIN,
    WAV_FORMAT,
)
from unmixer.ui.constants import FONT_WEIGHT_BOLD, OK_BUTTON_TEXT, settings
from unmixer.util import expand_path


"""
--flac
----
--mp3
--mp3-bitrate BITRATE  (int in kbps - default is 320)
--mp3-preset [2-7]  (2 --> best quality, 7 --> fastest)
----
--float32
--int24
(default: int16)

--name MODEL
--repo REPO  (folder containing all pre-trained models for use with -n)
----
--sig SIG  (locally trained XP signature)

--out OUT  (output directory)
--filename FILENAME  Use "{track}", "{trackext}", "{stem}", "{ext}" to use variables of track name without extension,
                     track extension, stem name and default output file extension. Default is "{track}/{stem}.{ext}".

--no-split  (mutually exclusive with --segment)
--segment SEGMENT  (int, >=10 recommended)
--shifts SHIFTS  (makes prediction SHIFTS times slower - GPU only)
--overlap OVERLAP  (default is 0.25, reduce to 0.1 for speed improvement)

--clip-mode [clamp|rescale]  (default is rescale)

--device [cuda|cpu]  (default is cuda if available else cpu)
--jobs JOBS  (parallel jobs - also multiplies RAM usage by JOBS)

--verbose  (verbose output)

env var: PYTORCH_NO_CUDA_MEMORY_CACHING=1
"""

"""
Other pre-trained models can be selected with the -n flag. The list of pre-trained models is:
* htdemucs: first version of Hybrid Transformer Demucs. Trained on MusDB + 800 songs. Default model.
* htdemucs_ft: fine-tuned version of htdemucs, separation will take 4 times more time but might be a bit better. Same training set as htdemucs.
* htdemucs_6s: 6 sources version of htdemucs, with piano and guitar being added as sources. Note that the piano source is not working great at the moment.
* hdemucs_mmi: Hybrid Demucs v3, retrained on MusDB + 800 songs.
* mdx: trained only on MusDB HQ, winning model on track A at the MDX challenge.
* mdx_extra: trained with extra training data (including MusDB test set), ranked 2nd on the track B of the MDX challenge.
* mdx_q, mdx_extra_q: quantized version of the previous models. Smaller download and storage but quality can be slightly worse.
* SIG: where SIG is a single model from the model zoo.
"""

WAV_BIT_DEPTHS = {
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
    
    def __init__(self, dir_path: str, file_dialog_title: str = DEFAULT_FILE_DIALOG_TITLE) -> None:
        super().__init__()
        self.dir_path = expand_path(dir_path)
        self.file_dialog_title = file_dialog_title
        
        self.label = QLabel(self.dir_path)
        
        self.button = QPushButton(self.BUTTON_TEXT)
        self.button.setToolTip(self.BUTTON_TOOLTIP)
        self.button.clicked.connect(self.select_directory)
        
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.show()
    
    def select_directory(self) -> None:
        input_path = QFileDialog.getExistingDirectory(self.parent(), self.file_dialog_title,
                                                      self.dir_path, QFileDialog.Option.ShowDirsOnly)
        
        if not input_path:
            return
        
        self.dir_path = input_path
        self.label.setText(self.dir_path)
        self.changed.emit(self.dir_path)
        self.update()


class UnmixerPreferences(QWidget):

    ADVANCED_SECTION_HEADING = 'Advanced Settings'
    ISOLATED_TRACK_IMPORT_SECTION_HEADING = 'Isolated Track Import'
    
    AUDIO_FORMAT_LABEL = 'Output Format'
    
    MP3_BITRATE_LABEL = 'MP3 Bitrate'
    MP3_BITRATE_UNIT_LABEL = 'kbps'
    
    BETTER_QUALITY_LABEL = 'Better Quality'
    FASTER_ENCODING_LABEL = 'Faster Encoding'
    MP3_PRESET_LABEL = 'MP3 Preset'
    
    OPEN_TRACK_EXPLORER_LABEL = 'Open Track Explorer when finished'
    
    OTHER_TRACK_LABEL = '"Other" Track Name'
    
    OUTPUT_DIRECTORY_LABEL = 'Output Directory'
    OUTPUT_DIRECTORY_FILE_DIALOG_TITLE = 'Select Output Directory'
    
    WAV_BIT_DEPTH_LABEL = 'WAV Bit Depth'

    HEADING_FONT_SIZE = 18
    
    LABEL_SPACING = 20
    
    # (left, top, right, bottom)
    NO_MARGIN = (0, 0, 0, 0)
    ROW_BOTTOM_MARGIN = (0, 0, 0, 15)
    ROW_TOP_MARGIN = (0, 5, 0, 0)
    ROW_TOP_BOTTOM_MARGIN = (0, 5, 0, 15)
    
    OK_BUTTON_WIDTH = 150

    def __init__(self, parent: QWidget, app: 'UnmixerUI') -> None:
        super().__init__(parent)
        self.app = app
        
        self.open_track_explorer_checkbox = QCheckBox()
        self.open_track_explorer_checkbox.setChecked(
            app.settings.value(settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED, True)
        )
        self.open_track_explorer_checkbox.toggled.connect(self.open_track_explorer_setting_toggled)
        
        self.output_dir = DirectorySelector(self.app.output_dir_path,
                                            file_dialog_title=self.OUTPUT_DIRECTORY_FILE_DIALOG_TITLE)
        self.output_dir.changed.connect(self.output_dir_changed)

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
        for other_name in ALLOWED_OTHER_TRACK_NAMES:
            name_button = QRadioButton(other_name.capitalize())
            if other_name == self.app.other_track_name:
                name_button.setChecked(True)
            self.other_track_button_layout.addWidget(name_button)
            self.other_track_button_group.addButton(name_button)
        
        self.mp3_preset_slider = QSlider(Qt.Orientation.Horizontal)
        self.mp3_preset_slider.setMinimum(MP3_PRESET_MIN)
        self.mp3_preset_slider.setMaximum(MP3_PRESET_MAX)
        self.mp3_preset_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.mp3_preset_slider.setTickInterval(1)
        self.mp3_preset_slider.setValue(
            app.settings.value(settings.prefs.MP3_PRESET, DEFAULT_MP3_PRESET)
        )
        self.mp3_preset_slider.valueChanged.connect(self.update_mp3_preset)
        
        self.mp3_preset_slider_layout = QHBoxLayout()
        self.mp3_preset_slider_layout.setContentsMargins(*self.NO_MARGIN)
        better_quality_label = QLabel(self.BETTER_QUALITY_LABEL)
        better_quality_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        better_quality_label.setContentsMargins(*self.ROW_TOP_MARGIN)
        self.mp3_preset_slider_layout.addWidget(better_quality_label)
        self.mp3_preset_slider_layout.addWidget(self.mp3_preset_slider)
        faster_encoding_label = QLabel(self.FASTER_ENCODING_LABEL)
        faster_encoding_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        faster_encoding_label.setContentsMargins(*self.ROW_TOP_MARGIN)
        self.mp3_preset_slider_layout.addWidget(faster_encoding_label)
        
        self.mp3_bitrate_combo_box = QComboBox()
        selected_bitrate = self.app.settings.value(settings.prefs.MP3_BITRATE, DEFAULT_MP3_BITRATE_KBPS)
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
        self.wav_bit_depth_button_layout.setContentsMargins(*self.ROW_TOP_BOTTOM_MARGIN)
        selected_bit_depth = self.app.settings.value(settings.prefs.WAV_BIT_DEPTH, DEFAULT_WAV_DEPTH)
        for name, value in WAV_BIT_DEPTHS.items():
            depth_button = QRadioButton(name)
            if value == selected_bit_depth:
                depth_button.setChecked(True)
            self.wav_bit_depth_button_layout.addWidget(depth_button)
            self.wav_bit_depth_button_group.addButton(depth_button)
        
        self.ok_button = QPushButton(OK_BUTTON_TEXT)
        self.ok_button.setAutoDefault(True)
        self.ok_button.setDefault(True)
        self.ok_button.setFixedWidth(self.OK_BUTTON_WIDTH)
        self.ok_button.clicked.connect(self.parent().close)
        
        self.form_layout = QFormLayout()
        self.create_form_layout()
        
        layout = QVBoxLayout()
        layout.addLayout(self.form_layout)
        sublayout = QHBoxLayout()
        sublayout.setAlignment(Qt.AlignmentFlag.AlignRight)
        sublayout.addWidget(self.ok_button)
        layout.addLayout(sublayout)
        self.setLayout(layout)
        self.show()
    
    def create_form_layout(self) -> None:
        self.form_layout.setHorizontalSpacing(self.LABEL_SPACING)
        
        # Isolated Track Import
        self.add_section_heading(self.ISOLATED_TRACK_IMPORT_SECTION_HEADING, include_top_padding=False)

        # Output Directory
        output_dir_label = QLabel(self.OUTPUT_DIRECTORY_LABEL)
        font = output_dir_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        output_dir_label.setFont(font)
        self.form_layout.addRow(output_dir_label, self.output_dir)
        
        # Output Format
        audio_format_label = QLabel(self.AUDIO_FORMAT_LABEL)
        audio_format_label.setContentsMargins(*self.ROW_BOTTOM_MARGIN)
        font = audio_format_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        audio_format_label.setFont(font)
        self.form_layout.addRow(audio_format_label, self.audio_format_button_layout)
        
        # "Other" Track Name
        other_track_label = QLabel(self.OTHER_TRACK_LABEL)
        other_track_label.setContentsMargins(*self.ROW_BOTTOM_MARGIN)
        font = other_track_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        other_track_label.setFont(font)
        self.form_layout.addRow(other_track_label, self.other_track_button_layout)
        
        # Open Track Explorer when finished
        open_track_explorer_label = QLabel(self.OPEN_TRACK_EXPLORER_LABEL)
        open_track_explorer_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        font = open_track_explorer_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        open_track_explorer_label.setFont(font)
        self.form_layout.addRow(open_track_explorer_label, self.open_track_explorer_checkbox)
        
        # Advanced Settings
        self.add_section_heading(self.ADVANCED_SECTION_HEADING)
        
        # MP3 Preset
        mp3_preset_label = QLabel(self.MP3_PRESET_LABEL)
        mp3_preset_label.setContentsMargins(*self.ROW_TOP_BOTTOM_MARGIN)
        font = mp3_preset_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        mp3_preset_label.setFont(font)
        self.form_layout.addRow(mp3_preset_label, self.mp3_preset_slider_layout)

        # MP3 Bitrate
        mp3_bitrate_label = QLabel(self.MP3_BITRATE_LABEL)
        font = mp3_bitrate_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        mp3_bitrate_label.setFont(font)
        self.form_layout.addRow(mp3_bitrate_label, self.mp3_bitrate_combo_box_layout)

        # WAV Bit Depth
        wav_bit_depth_label = QLabel(self.WAV_BIT_DEPTH_LABEL)
        wav_bit_depth_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        wav_bit_depth_label.setContentsMargins(*self.ROW_TOP_BOTTOM_MARGIN)
        font = wav_bit_depth_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        wav_bit_depth_label.setFont(font)
        self.form_layout.addRow(wav_bit_depth_label, self.wav_bit_depth_button_layout)

        if self.app.output_format != MP3_FORMAT:
            self.hide_mp3_preferences()
        if self.app.output_format != WAV_FORMAT:
            self.hide_wav_preferences()
    
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
    
    def open_track_explorer_setting_toggled(self) -> None:
        show_track_explorer = self.open_track_explorer_checkbox.isChecked()
        self.app.settings.setValue(settings.prefs.SHOW_TRACK_EXPLORER_WHEN_IMPORT_FINISHED, show_track_explorer)
    
    def output_dir_changed(self, new_output_dir_path: str) -> None:
        if new_output_dir_path != self.app.output_dir_path:
            self.app.settings.setValue(settings.importer.OUTPUT_DIR_PATH, new_output_dir_path)
            self.app.output_dir_path = new_output_dir_path
    
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
            self.app.settings.setValue(settings.importer.AUDIO_FORMAT, audio_format)
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
            self.app.settings.setValue(settings.prefs.OTHER_TRACK_NAME, track_name)

            if self.app.import_window:
                self.app.import_window.set_other_track_name(self.app.other_track_name)
    
    def update_mp3_bitrate(self) -> None:
        mp3_bitrate = int(self.mp3_bitrate_combo_box.currentText())
        self.app.settings.setValue(settings.prefs.MP3_BITRATE, mp3_bitrate)
    
    def update_mp3_preset(self) -> None:
        mp3_preset = max(MP3_PRESET_MIN, min(self.mp3_preset_slider.value(), MP3_PRESET_MAX))
        self.app.settings.setValue(settings.prefs.MP3_PRESET, mp3_preset)
    
    def update_wav_bit_depth(self, button: QRadioButton, checked: bool) -> None:
        if checked:
            self.app.settings.setValue(settings.prefs.WAV_BIT_DEPTH, WAV_BIT_DEPTHS[button.text()])
