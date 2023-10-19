from multiprocessing import Process
from typing import Optional
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from unmixer.constants import (
    ALLOWED_OTHER_TRACK_NAMES,
    DEFAULT_ISOLATED_TRACK_FORMAT,
    DEFAULT_OTHER_TRACK_NAME,
    DEFAULT_OUTPUT_DIR,
    ISOLATED_TRACK_FORMATS,
    MP3_FORMAT,
)
from unmixer.remix import create_isolated_tracks_from_audio_file
from unmixer.ui.constants import (
    ERROR_MESSAGE_TITLE,
    FONT_WEIGHT_BOLD,
    IMPORT_AUDIO_FORMAT_SETTING_KEY,
    IMPORT_DIR_PATH_SETTING_KEY,
    OTHER_TRACK_NAME_SETTING_KEY,
)


class SongImportSettings(QWidget):

    AUDIO_FORMAT_LABEL = 'Isolated Track Output Format'
    OTHER_TRACK_LABEL = '"Other" Track Name'

    LABEL_SPACING = 20

    def __init__(self, app: 'UnmixerUI') -> None:
        super().__init__()
        self.app = app
        if self.app.other_track_name:
            self.other_track_name = self.app.other_track_name
        else:
            self.other_track_name = self.app.settings.value(OTHER_TRACK_NAME_SETTING_KEY, DEFAULT_OTHER_TRACK_NAME)
            if self.other_track_name != self.app.other_track_name:
                self.app.other_track_name = self.other_track_name
        if self.app.output_mp3_format:
            self.audio_format = MP3_FORMAT
        else:
            self.audio_format = self.app.settings.value(IMPORT_AUDIO_FORMAT_SETTING_KEY,
                                                        DEFAULT_ISOLATED_TRACK_FORMAT).lower()

        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(self.LABEL_SPACING)

        self.audio_format_label = QLabel(self.AUDIO_FORMAT_LABEL)
        font = self.audio_format_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        self.audio_format_label.setFont(font)

        self.audio_format_button_group = QButtonGroup()
        self.audio_format_button_group.setExclusive(True)
        self.audio_format_button_group.buttonToggled.connect(self.update_audio_format)

        audio_format_button_layout = QHBoxLayout()
        for audio_format in sorted(list(ISOLATED_TRACK_FORMATS)):
            format_button = QRadioButton(audio_format.upper())
            if audio_format == self.audio_format:
                format_button.setChecked(True)
            audio_format_button_layout.addWidget(format_button)
            self.audio_format_button_group.addButton(format_button)

        self.other_track_label = QLabel(self.OTHER_TRACK_LABEL)
        font = self.other_track_label.font()
        font.setWeight(FONT_WEIGHT_BOLD)
        self.other_track_label.setFont(font)

        self.other_track_button_group = QButtonGroup()
        self.other_track_button_group.setExclusive(True)
        self.other_track_button_group.buttonToggled.connect(self.update_other_track_name)

        other_track_button_layout = QHBoxLayout()
        for other_name in ALLOWED_OTHER_TRACK_NAMES:
            name_button = QRadioButton(other_name.capitalize())
            if other_name == self.other_track_name:
                name_button.setChecked(True)
            other_track_button_layout.addWidget(name_button)
            self.other_track_button_group.addButton(name_button)

        form_layout.addRow(self.audio_format_label, audio_format_button_layout)
        form_layout.addRow(self.other_track_label, other_track_button_layout)
        self.setLayout(form_layout)
        self.show()

    def update_audio_format(self, button: QRadioButton, checked: bool) -> None:
        if checked and (audio_format := button.text().lower()) != self.audio_format:
            self.audio_format = audio_format
            self.app.settings.setValue(IMPORT_AUDIO_FORMAT_SETTING_KEY, audio_format)

    def update_other_track_name(self, button: QRadioButton, checked: bool) -> None:
        if checked and (track_name := button.text().lower()) != self.other_track_name:
            self.other_track_name = track_name
            self.app.other_track_name = track_name
            self.app.settings.setValue(OTHER_TRACK_NAME_SETTING_KEY, track_name)

    def disable_form(self) -> None:
        for button in self.audio_format_button_group.buttons():
            button.setDisabled(True)
        for button in self.other_track_button_group.buttons():
            button.setDisabled(True)

    def enable_form(self) -> None:
        for button in self.audio_format_button_group.buttons():
            button.setDisabled(False)
        for button in self.other_track_button_group.buttons():
            button.setDisabled(False)


class SongImporter(QWidget):
    
    EXPLORE_BUTTON_TEXT = '🎛️ Explore isolated tracks...'
    EXPLORE_BUTTON_TOOLTIP = 'Select a directory containing previously isolated tracks to explore.'

    CHOOSE_BUTTON_TEXT = '📂 Choose a song...'
    CHOOSE_BUTON_TOOLTIP = 'Select a new song to create isolated tracks from.'
    CHOOSE_DIFFERENT_SONG_BUTTON_TEXT = '📂 Choose a different song...'
    CHOOSE_DIALOG_TITLE = 'Select a Song'

    START_BUTTON_TEXT = '✅ Start'
    CANCEL_BUTTON_TEXT = '❌ Cancel'
    
    DEFAULT_TITLE_TEXT = 'Select a song to unmix'
    IMPORTING_TITLE_TEXT_TEMPLATE = 'Now creating isolated tracks from:\n{filename}'
    SONG_SELECTED_TITLE_TEXT_TEMPLATE = 'Selected song:\n{filename}'

    DEFAULT_SUBTITLE_TEXT = 'You can also drop a song here from your computer.'
    IMPORTING_SUBTITLE_TEXT = (
        'Please wait; this may take some time.\n'
        'The time required is roughly equal to the length of the song itself.'
    )
    SONG_SELECTED_SUBTITLE_TEXT = f'Press [{START_BUTTON_TEXT}] to begin unmixing the song into isolated tracks.'
    
    IMPORT_STATUS_TIMER_INTERVAL_MILLIS = 1000
    
    MIN_BUTTON_HEIGHT = 50
    
    TITLE_FONT_SIZE = 20
    
    def __init__(self, app: 'UnmixerUI', input_file_path: Optional[str] = None,
                 output_dir_path: Optional[str] = None) -> None:
        super().__init__()
        self.app = app
        self.input_file_path = os.path.expanduser(input_file_path) if input_file_path else None
        self.output_dir_path = os.path.expanduser(output_dir_path or DEFAULT_OUTPUT_DIR)
        
        self._import_process = None
        self.check_import_status_timer = QTimer(self)
        self.check_import_status_timer.setInterval(self.IMPORT_STATUS_TIMER_INTERVAL_MILLIS)
        self.check_import_status_timer.timeout.connect(self.check_import_status)
        
        self.title = QLabel(self.DEFAULT_TITLE_TEXT)
        font = self.title.font()
        font.setPixelSize(self.TITLE_FONT_SIZE)
        font.setWeight(FONT_WEIGHT_BOLD)
        self.title.setFont(font)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.subtitle = QLabel(self.DEFAULT_SUBTITLE_TEXT)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setMinimumHeight(self.MIN_BUTTON_HEIGHT * 2)
        
        self.import_settings = SongImportSettings(app)

        self.explore_tracks_button = QPushButton(self.EXPLORE_BUTTON_TEXT)
        self.explore_tracks_button.setMinimumHeight(self.MIN_BUTTON_HEIGHT)
        self.explore_tracks_button.setToolTip(self.EXPLORE_BUTTON_TOOLTIP)
        self.explore_tracks_button.clicked.connect(self.app.choose_track_directory)

        self.choose_file_button = QPushButton(self.CHOOSE_BUTTON_TEXT)
        self.choose_file_button.setMinimumHeight(self.MIN_BUTTON_HEIGHT)
        self.choose_file_button.setToolTip(self.CHOOSE_BUTON_TOOLTIP)
        self.choose_file_button.clicked.connect(self.choose_file)
        
        self.start_import_button = QPushButton(self.START_BUTTON_TEXT)
        self.start_import_button.setAutoDefault(True)
        self.start_import_button.setDefault(True)
        self.start_import_button.setHidden(True)
        self.start_import_button.setMinimumHeight(self.MIN_BUTTON_HEIGHT)
        self.start_import_button.clicked.connect(self.start_import_button_pressed)

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.import_settings)
        layout.addWidget(self.explore_tracks_button)
        sublayout = QHBoxLayout()
        sublayout.addWidget(self.choose_file_button)
        sublayout.addWidget(self.start_import_button)
        layout.addLayout(sublayout)
        self.setLayout(layout)

        self.setFocusProxy(self.choose_file_button)
        self.show()
        
        if self.input_file_path:
            self.select_song()
        else:
            self.import_settings.disable_form()
            self.import_settings.setHidden(True)
    
    @property
    def import_process(self) -> Optional[Process]:
        return self._import_process
    
    def check_import_status(self) -> None:
        # Wait for import process to return/exit, then replace the import window with the track explorer.
        if self._import_process and not self._import_process.is_alive():
            self.check_import_status_timer.stop()
            return_code = self._import_process.exitcode
            self._import_process = None
            if return_code == 0:
                self.parent().app.show_track_explorer_window(source_file_path=self.input_file_path,
                                                             input_dir_path=self.output_dir_path)
            else:
                QMessageBox.critical(self.parent(), ERROR_MESSAGE_TITLE,
                                     f'An error occurred while unmixing {os.path.basename(self.input_file_path)}.')
    
    def choose_file(self) -> None:
        working_dir = self.parent().app.settings.value(IMPORT_DIR_PATH_SETTING_KEY, os.getcwd())
        input_path, _ = QFileDialog.getOpenFileName(self, self.CHOOSE_DIALOG_TITLE, working_dir)
        if not input_path:
            return
        
        self.input_file_path = input_path
        self.parent().app.settings.setValue(IMPORT_DIR_PATH_SETTING_KEY, os.path.dirname(input_path))
        self.select_song()

    def select_song(self) -> None:
        if not self.input_file_path:
            return

        if self.parent():
            self.parent().enable_import_menu_action()
            self.parent().setWindowTitle(self.parent().DEFAULT_WINDOW_TITLE)
            self.parent().update()

        filename = os.path.basename(self.input_file_path)
        self.title.setText(self.SONG_SELECTED_TITLE_TEXT_TEMPLATE.format(filename=filename))
        self.title.setToolTip(self.input_file_path)
        self.subtitle.setText(self.SONG_SELECTED_SUBTITLE_TEXT)
        self.import_settings.enable_form()
        self.import_settings.setHidden(False)
        self.choose_file_button.setDisabled(False)
        self.choose_file_button.setText(self.CHOOSE_DIFFERENT_SONG_BUTTON_TEXT)
        self.start_import_button.setHidden(False)
        self.start_import_button.setText(self.START_BUTTON_TEXT)
        self.start_import_button.setFocus()
        self.update()

    def start_import_button_pressed(self) -> None:
        if self._import_process is not None and self._import_process.is_alive():
            self.app.stop_import_process()
            self._import_process = None
            self.check_import_status_timer.stop()
            self.select_song()
        else:
            self.import_file()

    def import_file(self) -> None:
        if not self.input_file_path:
            return
        
        if self.parent():
            self.parent().disable_import_menu_action()
            self.parent().setWindowTitle(self.parent().IMPORTING_WINDOW_TITLE)
            self.parent().update()

        filename = os.path.basename(self.input_file_path)
        self.title.setText(self.IMPORTING_TITLE_TEXT_TEMPLATE.format(filename=filename))
        self.title.setToolTip(self.input_file_path)
        self.subtitle.setText(self.IMPORTING_SUBTITLE_TEXT)
        self.import_settings.disable_form()
        self.choose_file_button.setDisabled(True)
        self.start_import_button.setText(self.CANCEL_BUTTON_TEXT)
        self.update()

        self._import_process = Process(target=create_isolated_tracks_from_audio_file,
                                       args=(self.input_file_path, self.output_dir_path, self.app.other_track_name),
                                       kwargs={'output_mp3_format': self.import_settings.audio_format == MP3_FORMAT})
        self._import_process.start()
        self.check_import_status_timer.start()

    def reset(self) -> None:
        if self._import_process is not None and self._import_process.is_alive():
            self.app.stop_import_process()
            self.check_import_status_timer.stop()

        self._import_process = None
        self.input_file_path = None
        self.title.setText(self.DEFAULT_TITLE_TEXT)
        self.title.setToolTip('')
        self.subtitle.setText(self.DEFAULT_SUBTITLE_TEXT)
        self.import_settings.disable_form()
        self.import_settings.setHidden(True)
        self.choose_file_button.setText(self.CHOOSE_BUTTON_TEXT)
        self.choose_file_button.setDisabled(False)
        self.start_import_button.setText(self.START_BUTTON_TEXT)
        self.start_import_button.setHidden(True)
        self.update()
