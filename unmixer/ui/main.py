from typing import Optional
import os.path
import tempfile

from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from unmixer.constants import DEFAULT_OUTPUT_DIR
from unmixer.remix import merge_audio_files
from unmixer.ui.constants import APP_NAME, SUCCESS_MESSAGE_TITLE
from unmixer.ui.importer import SongImporter
from unmixer.ui.multitrack import MultiTrackDisplay
from unmixer.util import is_isolated_track


class UnmixerImportWindow(QMainWindow):
    
    DEFAULT_WINDOW_TITLE = f'{APP_NAME} | Select a Song'
    IMPORTING_WINDOW_TITLE = f'{APP_NAME} | Importing...'
    
    MIN_HEIGHT = 300
    MIN_WIDTH = 600
    
    def __init__(self, app: 'UnmixerUI', source_file_path: Optional[str] = None, output_dir_path: Optional[str] = None,
                 other_track_name: Optional[str] = None) -> None:
        super().__init__()
        self.app = app
        self.importer = SongImporter(source_file_path, output_dir_path, other_track_name=other_track_name)
        self.setCentralWidget(self.importer)
        self.setWindowTitle(self.DEFAULT_WINDOW_TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)


class UnmixerTrackExplorerWindow(QMainWindow):
    
    WINDOW_TITLE = f'{APP_NAME} | Track Explorer'
    
    MIN_HEIGHT = 800
    MIN_WIDTH = 1000

    def __init__(self, app: 'UnmixerUI', input_dir_path: str, source_file_path: Optional[str] = None,
                 other_track_name: Optional[str] = None) -> None:
        super().__init__()
        self.app = app
        
        self.source_file_path = os.path.expanduser(source_file_path) if source_file_path else None
        self.input_dir_path = os.path.expanduser(input_dir_path)
        self.song_title = os.path.basename(self.input_dir_path)
        file_paths = sorted(
            os.path.join(self.input_dir_path, filename)
            for filename in os.listdir(self.input_dir_path)
            if is_isolated_track(filename)
        )
        if len(file_paths) < 2:
            raise ValueError(f'Not enough isolated tracks to explore in "{self.input_dir_path}"!')
        
        self.tracks = MultiTrackDisplay(self.song_title, file_paths, other_track_name=other_track_name)
        self.setCentralWidget(self.tracks)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        
        self._temp_dir = None
        self._temp_file_paths = set()
        
    @property
    def temp_dir(self) -> tempfile.TemporaryDirectory:
        if self._temp_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix=f'unmixer_{self.song_title.replace(" ", "_")}_')
        return self._temp_dir
    
    @property
    def temp_dir_path(self) -> str:
        return self.temp_dir.name
    
    def _output_file_path(self, input_file_paths: list[str]) -> str:
        name = '+'.join(os.path.splitext(os.path.basename(path))[0] for path in sorted(input_file_paths))
        _, extension = os.path.splitext(input_file_paths[0])
        return os.path.join(self.temp_dir_path, name + extension)
    
    def temp_file_path(self, input_file_paths: list[str]) -> str:
        if not input_file_paths:
            raise ValueError('No input files provided!')
        if len(input_file_paths) == 1:
            return input_file_paths[0]
        if len(input_file_paths) == len(self.tracks.tracks) and self.source_file_path:
            return self.source_file_path
        if (output_path := self._output_file_path(input_file_paths)) not in self._temp_file_paths:
            self.create_temp_mix_file(input_file_paths)
            self._temp_file_paths.add(output_path)
        return output_path
    
    def create_temp_mix_file(self, input_file_paths: list[str]) -> None:
        if not input_file_paths or len(input_file_paths) < 2:
            raise ValueError('Not enough input files provided!')
        merge_audio_files(input_file_paths, self._output_file_path(input_file_paths))


class UnmixerUI:

    def __init__(self, song_path: Optional[str] = None, input_dir_path: Optional[str] = None,
                 output_dir_path: Optional[str] = None, other_track_name: Optional[str] = None) -> None:
        if song_path and input_dir_path:
            raise ValueError('Must provide song path or input directory path, but not both!')
        
        self.app = QApplication([])
        self.song_path = os.path.expanduser(song_path) if song_path else None
        self.input_dir_path = os.path.expanduser(input_dir_path) if input_dir_path else None
        self.output_dir_path = os.path.expanduser(output_dir_path or DEFAULT_OUTPUT_DIR)
        self.other_track_name = other_track_name
        self.import_window = None
        self.main_window = None
        
        if input_dir_path:
            self.main_window = UnmixerTrackExplorerWindow(self, input_dir_path=self.input_dir_path,
                                                          other_track_name=self.other_track_name)
        else:
            self.import_window = UnmixerImportWindow(self, source_file_path=self.song_path,
                                                     output_dir_path=self.output_dir_path,
                                                     other_track_name=self.other_track_name)

    def run(self) -> None:
        if self.main_window:
            self.main_window.show()
        else:
            self.import_window.show()
        self.app.aboutToQuit.connect(self.stop_import_process)
        self.app.exec()
        
    def stop_import_process(self) -> None:
        if self.import_window and ((import_process := self.import_window.importer.import_process) and import_process.is_alive()):
            import_process.terminate()
        
    def show_track_explorer_window(self, source_file_path: Optional[str] = None) -> None:
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        # The isolated tracks are in a subdirectory of self.output_dir_path named for the song title.
        dir_path = self.output_dir_path
        if source_file_path:
            song_title = os.path.splitext(os.path.basename(source_file_path))[0]
            dir_path = os.path.join(dir_path, song_title)
        
        self.main_window = UnmixerTrackExplorerWindow(self, input_dir_path=dir_path,
                                                      source_file_path=source_file_path,
                                                      other_track_name=self.other_track_name)
        self.main_window.show()
        QMessageBox.information(self.main_window, SUCCESS_MESSAGE_TITLE,
                                f'Successfully wrote isolated tracks to {dir_path}.')
        
        if self.import_window:
            self.import_window.close()
            self.import_window = None
