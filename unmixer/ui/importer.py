from multiprocessing import Process
from typing import Optional
import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from unmixer.constants import DEFAULT_OUTPUT_DIR
from unmixer.remix import create_isolated_tracks_from_audio_file
from unmixer.ui.constants import FONT_WEIGHT_BOLD


def import_audio_file(input_file_path: str, output_dir_path: str, other_track_name: Optional[str]) -> None:
    create_isolated_tracks_from_audio_file(input_file_path, output_dir_path, other_track_name)


class SongImporter(QWidget):
    
    CHOOSE_BUTTON_TEXT = '📂 Choose...'
    CHOOSE_DIALOG_TITLE = f'Select a Song'
    
    DEFAULT_TITLE_TEXT = 'Select a song to unmix'
    SUBTITLE_TEXT = (
        'Please wait; this may take some time.\n'
        'The time required is roughly equal to the length of the song itself.'
    )
    
    IMPORT_STATUS_TIMER_INTERVAL_MILLIS = 1000
    
    MIN_BUTTON_HEIGHT = 50
    
    TITLE_FONT_SIZE = 20
    
    def __init__(self, input_file_path: Optional[str] = None, output_dir_path: Optional[str] = None,
                 other_track_name: Optional[str] = None) -> None:
        super().__init__()
        self.input_file_path = os.path.expanduser(input_file_path) if input_file_path else None
        self.output_dir_path = os.path.expanduser(output_dir_path or DEFAULT_OUTPUT_DIR)
        self.other_track_name = other_track_name
        
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
        
        self.subtitle = QLabel('')
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setHidden(True)
        
        self.choose_file_button = QPushButton(self.CHOOSE_BUTTON_TEXT)
        self.choose_file_button.setMinimumHeight(self.MIN_BUTTON_HEIGHT)
        self.choose_file_button.clicked.connect(self.choose_file)
        
        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.choose_file_button)
        self.setLayout(layout)
        self.show()
        
        if self.input_file_path:
            self.import_file()
    
    @property
    def import_process(self) -> Optional[Process]:
        return self._import_process
    
    def check_import_status(self) -> None:
        # Wait for import process to return/exit, then replace the import window with the track explorer.
        if self._import_process and not self._import_process.is_alive():
            self._import_process = None
            self.check_import_status_timer.stop()
            self.parent().app.show_track_explorer_window(source_file_path=self.input_file_path)
    
    def choose_file(self) -> None:
        input_path, _ = QFileDialog.getOpenFileName(self, self.CHOOSE_DIALOG_TITLE, os.getcwd())
        if not input_path:
            return
        
        self.input_file_path = input_path
        self.import_file()
    
    def import_file(self) -> None:
        if not self.input_file_path:
            return
        
        filename = os.path.basename(self.input_file_path)
        self.parent().setWindowTitle(self.parent().IMPORTING_WINDOW_TITLE)
        self.title.setText(f'Now creating isolated tracks from:\n{filename}')
        self.subtitle.setText(self.SUBTITLE_TEXT)
        self.subtitle.setHidden(False)
        self.choose_file_button.setDisabled(True)
        self._import_process = Process(target=import_audio_file,
                                       args=(self.input_file_path, self.output_dir_path, self.other_track_name))
        self._import_process.start()
        self.check_import_status_timer.start()
        self.parent().update()
