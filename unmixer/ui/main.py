from typing import Callable, Optional
import abc
import os.path
import tempfile

from PyQt6.QtCore import QSettings, Qt, QUrl
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
)

from unmixer.constants import DEFAULT_OUTPUT_DIR
from unmixer.remix import merge_audio_files
from unmixer.ui.constants import (
    APP_NAME,
    IMPORT_DIR_PATH_SETTING_KEY,
    OPEN_TRACK_DIR_PATH_SETTING_KEY,
    OTHER_TRACK_NAME_SETTING_KEY,
    ORGANIZATION_NAME,
    PROJECT_README_URL,
    RECENTLY_OPENED_SETTING_KEY,
    SUCCESS_MESSAGE_TITLE,
)
from unmixer.ui.importer import SongImporter
from unmixer.ui.multitrack import MultiTrackDisplay
from unmixer.ui.track import Track
from unmixer.util import cleanup_intermediate_dir, is_isolated_track


class UnmixerMainWindow(QMainWindow):

    EXPORT_MENU_ACTION_KEY = 'export'
    IMPORT_MENU_ACTION_KEY = 'import'
    PLAY_MENU_ACTION_KEY = 'play'

    STATUS_BAR_FONT_SIZE = 10
    STATUS_MESSAGE_DURATION_MILLIS = 1_000

    def __init__(self, app: 'UnmixerUI', show_status_bar: bool = True) -> None:
        super().__init__()
        self.app = app
        self.menu_bar = QMenuBar(self)
        self._menu_actions = {}

        if show_status_bar:
            status_bar_font = self.statusBar().font()
            status_bar_font.setPixelSize(self.STATUS_BAR_FONT_SIZE)
            self.statusBar().setFont(status_bar_font)
            self.statusBar().setMaximumHeight(int(self.STATUS_BAR_FONT_SIZE * 1.5))

    @abc.abstractmethod
    def create_menu_bar(self) -> None:
        raise NotImplemented

    def focusInEvent(self, event):
        self.app.active_window = self

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            for window in list(self.app.track_windows.values()):
                if window is self:
                    if window.input_dir_path in self.app.track_windows:
                        del self.app.track_windows[window.input_dir_path]
                else:
                    window.reset_menu_bar()
            if self.app.import_window:
                if self.app.import_window is self:
                    self.app.import_window = None
                else:
                    self.app.import_window.reset_menu_bar()
        finally:
            event.accept()

    def reset_menu_bar(self) -> None:
        self.menu_bar.clear()
        self.create_menu_bar()

    def create_file_menu(self) -> QMenu:
        file_menu = self.menu_bar.addMenu('&File')
        self.menu_bar.addAction(file_menu.menuAction())

        # File > Open Isolated Tracks...
        open_tracks_action = file_menu.addAction('&Open Isolated Tracks...')
        open_tracks_action.setShortcut(QKeySequence.StandardKey.Open)
        open_tracks_action.triggered.connect(self.app.choose_track_directory)

        # File > Open Recent
        recent_menu = file_menu.addMenu('Open Recent')
        file_menu.addAction(recent_menu.menuAction())

        # File > Open Recent > [Song Title]
        recently_opened = self.app.settings.value(RECENTLY_OPENED_SETTING_KEY, [], 'QStringList')
        for recent_dir_path in recently_opened:
            # TODO - ensure path still exists before adding it to the menu (if not, update settings)
            song_title = os.path.basename(recent_dir_path.rstrip(os.path.sep))
            open_action = recent_menu.addAction(song_title)
            open_action.setStatusTip(recent_dir_path)
            open_action.setToolTip(recent_dir_path)
            open_action.triggered.connect(self.open_recent_menu_action(recent_dir_path))

        return file_menu

    def add_close_action_to_file_menu(self, file_menu: QMenu) -> None:
        # File > Close
        file_menu.addSeparator()
        close_window_action = file_menu.addAction('&Close')
        close_window_action.setShortcut(QKeySequence.StandardKey.Close)
        close_window_action.triggered.connect(self.close)

    def create_window_menu(self) -> None:
        window_menu = self.menu_bar.addMenu('&Window')
        self.menu_bar.addAction(window_menu.menuAction())

        # Window > Song Importer
        song_importer_action = window_menu.addAction('&Song Importer')
        song_importer_action.setShortcut(QKeySequence('Ctrl+0'))
        song_importer_action.triggered.connect(self.app.bring_import_window_to_front)

        # Window > Track Explorer - [Song Title]
        if self.app.track_windows or isinstance(self, UnmixerTrackExplorerWindow):
            window_menu.addSeparator()
            track_windows = list(self.app.track_windows.values())
            if self not in track_windows and isinstance(self, UnmixerTrackExplorerWindow):
                track_windows.append(self)
            for i, track_window in enumerate(sorted(track_windows, key=lambda w: w.song_title)):
                track_explorer_action = window_menu.addAction(f'&Track Explorer - {track_window.song_title}')
                if (index := i + 1) < 10:
                    track_explorer_action.setShortcut(QKeySequence(f'Ctrl+T,Ctrl+{index}'))
                track_explorer_action.triggered.connect(track_window.bring_to_front)

    def create_help_menu(self) -> None:
        help_menu = self.menu_bar.addMenu('&Help')
        self.menu_bar.addAction(help_menu.menuAction())

        # Help > About...
        # NOTE: On macOS, this will appear under the application (Python) menu instead of the Help menu.
        about_action = help_menu.addAction('&About...')
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        about_action.triggered.connect(self.app.open_project_readme)

    def open_recent_menu_action(self, dir_path: str) -> Callable[[], None]:
        def handler():
            self.app.show_track_explorer_window(input_dir_path=dir_path, show_success_message=False)
        return handler

    def bring_to_front(self) -> None:
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def show_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, self.STATUS_MESSAGE_DURATION_MILLIS)
        self.update()
        QApplication.processEvents()


class UnmixerImportWindow(UnmixerMainWindow):

    DEFAULT_WINDOW_TITLE = f'{APP_NAME} | Select a Song'
    IMPORTING_WINDOW_TITLE = f'{APP_NAME} | Importing...'

    MIN_HEIGHT = 400
    MIN_WIDTH = 600

    def __init__(self, app: 'UnmixerUI', source_file_path: Optional[str] = None,
                 output_dir_path: Optional[str] = None) -> None:
        super().__init__(app, show_status_bar=False)
        self.importer = SongImporter(app, source_file_path, output_dir_path)
        self.setCentralWidget(self.importer)
        self.setWindowTitle(self.DEFAULT_WINDOW_TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.setAcceptDrops(True)
        self.create_menu_bar()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self.importer.import_process is not None and self.importer.import_process.is_alive():
            event.ignore()
        else:
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self.importer.import_process is not None and self.importer.import_process.is_alive():
            event.ignore()
        else:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        input_path = None
        for url in event.mimeData().urls():
            if url.isLocalFile():
                input_path = url.toLocalFile()
                event.acceptProposedAction()
                break

        if input_path is None:
            event.ignore()
            return

        if os.path.isdir(input_path):
            self.app.output_dir_path = input_path
            self.app.settings.setValue(OPEN_TRACK_DIR_PATH_SETTING_KEY, os.path.dirname(input_path))
            self.app.show_track_explorer_window(input_dir_path=input_path, show_success_message=False)
        else:
            self.app.song_path = input_path
            self.importer.input_file_path = input_path
            self.app.settings.setValue(IMPORT_DIR_PATH_SETTING_KEY, os.path.dirname(input_path))
            self.importer.select_song()

    def create_menu_bar(self) -> None:
        # File menu
        file_menu = self.create_file_menu()
        file_menu.addSeparator()

        # File > Import Song...
        import_song_action = file_menu.addAction('&Import Song...')
        import_song_action.setShortcut(QKeySequence('Ctrl+I'))
        import_song_action.triggered.connect(self.importer.choose_file)
        self._menu_actions[self.IMPORT_MENU_ACTION_KEY] = import_song_action

        # File > Close
        self.add_close_action_to_file_menu(file_menu)

        # Window menu
        self.create_window_menu()

        # Help menu
        self.create_help_menu()

    def enable_import_menu_action(self) -> None:
        self._menu_actions[self.IMPORT_MENU_ACTION_KEY].setDisabled(False)

    def disable_import_menu_action(self) -> None:
        self._menu_actions[self.IMPORT_MENU_ACTION_KEY].setDisabled(True)

    def reset(self) -> None:
        self.setWindowTitle(self.DEFAULT_WINDOW_TITLE)
        self.reset_menu_bar()
        self.importer.reset()
        self.update()


class UnmixerTrackExplorerWindow(UnmixerMainWindow):

    WINDOW_TITLE = f'{APP_NAME} | Track Explorer'

    MIN_HEIGHT = 800
    MIN_WIDTH = 1000

    FFMPEG_THREAD_SLEEP_TIME_SECONDS = 0.1

    def __init__(self, app: 'UnmixerUI', input_dir_path: str, source_file_path: Optional[str] = None,
                 other_track_name: Optional[str] = None) -> None:
        super().__init__(app)

        # Optimization only: store the source file path after importing a file
        # to avoid the need to create a full mix on-the-fly using ffmpeg.
        self.source_file_path = os.path.expanduser(source_file_path) if source_file_path else None
        self.input_dir_path = os.path.expanduser(input_dir_path)
        self.song_title = os.path.basename(self.input_dir_path.rstrip(os.path.sep))
        file_paths = sorted(
            os.path.join(self.input_dir_path, filename)
            for filename in os.listdir(self.input_dir_path)
            if is_isolated_track(filename)
        )
        if len(file_paths) < 2:
            raise ValueError(f'Not enough isolated tracks to explore in "{self.input_dir_path}"!')

        self.tracks = MultiTrackDisplay(self, self.song_title, file_paths, other_track_name=other_track_name)
        self.setCentralWidget(self.tracks)
        self.setWindowTitle(f'{self.WINDOW_TITLE} - {self.song_title}')
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.create_menu_bar()
        
        self.statusBar().addPermanentWidget(QLabel(self.input_dir_path))

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

    def closeEvent(self, event: QCloseEvent):
        if self.tracks.player and self.tracks.player.isPlaying():
            self.tracks.player.stop()
        super().closeEvent(event)

    def create_menu_bar(self) -> None:
        # File menu
        file_menu = self.create_file_menu()
        file_menu.addSeparator()

        # File > Export...
        export_action = file_menu.addAction('E&xport...')
        export_action.setDisabled(True)  # Initially, all tracks are selected, so exporting is disabled.
        export_action.setShortcut(QKeySequence.StandardKey.Save)
        export_action.triggered.connect(self.tracks.export_selected_tracks)
        self._menu_actions[self.EXPORT_MENU_ACTION_KEY] = export_action

        # File > Close
        self.add_close_action_to_file_menu(file_menu)

        # Edit menu
        self._create_edit_menu()

        # Controls menu
        self._create_controls_menu()

        # Window menu
        self.create_window_menu()

        # Help menu
        self.create_help_menu()

        # TODO
        # NOTE: On macOS, this will appear under the application (Python) menu instead of the File menu.
        # preferences_action = file_menu.addAction('Preferences...')
        # preferences_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        # preferences_action.setShortcut(QKeySequence.StandardKey.Preferences)
        # preferences_action.triggered.connect(lambda: None)

    def _create_edit_menu(self) -> None:
        edit_menu = self.menu_bar.addMenu('&Edit')
        self.menu_bar.addAction(edit_menu.menuAction())

        for i, track in enumerate(self.tracks.tracks):
            # Edit > Mute/Unmute [Track]
            track_name = track.controls.name.text()
            mute_action = edit_menu.addAction(f'Mute {track_name}')
            mute_action.setShortcut(QKeySequence(f'Ctrl+M,Ctrl+{i+1}'))
            mute_action.triggered.connect(self.mute_menu_action(track))
            self._menu_actions[f'mute_{track_name}'] = mute_action

            # Edit > Solo/Unsolo [Track]
            solo_action = edit_menu.addAction(f'Solo {track_name}')
            solo_action.setShortcut(QKeySequence(f'Ctrl+L,Ctrl+{i+1}'))
            solo_action.triggered.connect(self.solo_menu_action(track))
            self._menu_actions[f'solo_{track_name}'] = solo_action

            if i < len(self.tracks.tracks) - 1:
                edit_menu.addSeparator()

    def _create_controls_menu(self) -> None:
        controls_menu = self.menu_bar.addMenu('&Controls')
        self.menu_bar.addAction(controls_menu.menuAction())

        # Controls > Play/Pause
        play_action = controls_menu.addAction('&Play')
        play_action.setShortcut(QKeySequence(Qt.Key.Key_Space))
        play_action.triggered.connect(self.play_menu_action)
        self._menu_actions[self.PLAY_MENU_ACTION_KEY] = play_action

        controls_menu.addSeparator()

        # Controls > Restart
        restart_action = controls_menu.addAction('&Restart')
        restart_action.setShortcut(QKeySequence('Ctrl+Left'))
        restart_action.triggered.connect(self.tracks.controls.restart_track)

        # Controls > Skip Back
        skip_back_action = controls_menu.addAction('Skip &Back')
        skip_back_action.setShortcut(QKeySequence(Qt.Key.Key_Left))
        skip_back_action.triggered.connect(self.tracks.controls.skip_back)

        # Controls > Skip Forward
        skip_forward_action = controls_menu.addAction('Skip &Forward')
        skip_forward_action.setShortcut(QKeySequence(Qt.Key.Key_Right))
        skip_forward_action.triggered.connect(self.tracks.controls.skip_forward)

        controls_menu.addSeparator()

        # Controls > Increase Volume
        increase_volume_action = controls_menu.addAction('&Increase Volume')
        increase_volume_action.setShortcut(QKeySequence('Ctrl+Up'))
        increase_volume_action.triggered.connect(self.tracks.controls.increase_volume)

        # Controls > Decrease Volume
        decrease_volume_action = controls_menu.addAction('&Decrease Volume')
        decrease_volume_action.setShortcut(QKeySequence('Ctrl+Down'))
        decrease_volume_action.triggered.connect(self.tracks.controls.decrease_volume)

    def output_file_path(self, input_file_paths: list[str]) -> str:
        name = '+'.join(os.path.splitext(os.path.basename(path))[0] for path in sorted(input_file_paths))
        _, extension = os.path.splitext(input_file_paths[0])
        return os.path.join(self.temp_dir_path, name + extension)
    
    def has_temp_mix_file(self, input_file_paths: list[str]) -> bool:
        if not input_file_paths:
            raise ValueError('No input files provided!')
        if len(input_file_paths) == 1 or (len(input_file_paths) == len(self.tracks.tracks) and self.source_file_path):
            return True
        return self.output_file_path(input_file_paths) in self._temp_file_paths

    # NOTE: This will create the temp mix file using ffmpeg if it does not exist already!
    def temp_file_path(self, input_file_paths: list[str]) -> str:
        if not input_file_paths:
            raise ValueError('No input files provided!')
        if len(input_file_paths) == 1:
            return input_file_paths[0]
        if len(input_file_paths) == len(self.tracks.tracks) and self.source_file_path:
            return self.source_file_path
        if (output_path := self.output_file_path(input_file_paths)) not in self._temp_file_paths:
            self.create_temp_mix_file(input_file_paths)
            self._temp_file_paths.add(output_path)
        return output_path

    def create_temp_mix_file(self, input_file_paths: list[str]) -> None:
        if not input_file_paths or len(input_file_paths) < 2:
            raise ValueError('Not enough input files provided!')
        output_path = self.output_file_path(input_file_paths)
        print(f'Creating temporary mix file "{output_path}"...')
        merge_audio_files(input_file_paths, output_path)

    def play_menu_action(self) -> None:
        self.tracks.controls.toggle_playback()
        self._menu_actions[self.PLAY_MENU_ACTION_KEY].setText('&Pause' if self.tracks.controls.playing else '&Play')

    def mute_menu_action(self, track: Track) -> Callable[[], None]:
        def handler():
            name = track.controls.name.text()
            track.controls.toggle_muted()
            self._menu_actions[f'mute_{name}'].setText(f'Unmute {name}' if track.muted else f'Mute {name}')
        return handler

    def solo_menu_action(self, track: Track) -> Callable[[], None]:
        def handler():
            prev_soloed_track = self.tracks.soloed_track
            name = track.controls.name.text()
            track.controls.toggle_soloed()
            self._menu_actions[f'solo_{name}'].setText(f'Unsolo {name}' if track.soloed else f'Solo {name}')
            self._menu_actions[f'mute_{name}'].setDisabled(track.soloed)
            if prev_soloed_track and prev_soloed_track != track:
                prev_name = prev_soloed_track.controls.name.text()
                self._menu_actions[f'solo_{prev_name}'].setText(f'Solo {prev_name}')
        return handler

    def enable_export_menu_action(self) -> None:
        self._menu_actions[self.EXPORT_MENU_ACTION_KEY].setDisabled(False)

    def disable_export_menu_action(self) -> None:
        self._menu_actions[self.EXPORT_MENU_ACTION_KEY].setDisabled(True)


class UnmixerUI:

    CHOOSE_TRACK_DIR_DIALOG_TITLE = 'Open Isolated Tracks Directory'

    MAX_RECENTLY_OPENED_SONGS = 10

    def __init__(self, song_path: Optional[str] = None, input_dir_path: Optional[str] = None,
                 output_dir_path: Optional[str] = None, output_mp3_format: bool = False,
                 other_track_name: Optional[str] = None) -> None:
        if song_path and input_dir_path:
            raise ValueError('Must provide song path or input directory path, but not both!')
        
        self.app = QApplication([])
        self.settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        self.song_path = os.path.abspath(os.path.expanduser(song_path)) if song_path else None
        self.input_dir_path = os.path.abspath(os.path.expanduser(input_dir_path)) if input_dir_path else None
        self.output_dir_path = os.path.abspath(os.path.expanduser(output_dir_path or DEFAULT_OUTPUT_DIR))
        self.output_mp3_format = output_mp3_format
        self.other_track_name = other_track_name
        self.import_window = None
        self.track_windows = {}
        self.active_window = None
        
        if self.other_track_name:
            self.settings.setValue(OTHER_TRACK_NAME_SETTING_KEY, self.other_track_name)

        if self.input_dir_path:
            self.track_windows[self.input_dir_path] = UnmixerTrackExplorerWindow(self,
                                                                                 input_dir_path=self.input_dir_path,
                                                                                 other_track_name=self.other_track_name)
            self.add_song_to_recently_opened()
        else:
            self.import_window = UnmixerImportWindow(self, source_file_path=self.song_path,
                                                     output_dir_path=self.output_dir_path)

    @staticmethod
    def open_project_readme() -> None:
        QDesktopServices.openUrl(QUrl(PROJECT_README_URL))

    def choose_track_directory(self) -> None:
        working_dir = self.settings.value(OPEN_TRACK_DIR_PATH_SETTING_KEY, os.path.expanduser(DEFAULT_OUTPUT_DIR))
        input_path = QFileDialog.getExistingDirectory(self.active_window, self.CHOOSE_TRACK_DIR_DIALOG_TITLE,
                                                      working_dir, QFileDialog.Option.ShowDirsOnly)
        if not input_path:
            return

        self.settings.setValue(OPEN_TRACK_DIR_PATH_SETTING_KEY, os.path.dirname(input_path))
        self.input_dir_path = input_path
        self.show_track_explorer_window(input_dir_path=input_path, show_success_message=False)

    def run(self) -> None:
        active_window = None
        if self.track_windows:
            for window in self.track_windows.values():
                active_window = window
                window.show()
        if self.import_window:
            active_window = self.import_window
            self.import_window.show()
        self.active_window = active_window
        self.app.aboutToQuit.connect(self.stop_import_process)
        self.app.exec()
        
    def stop_import_process(self) -> None:
        if self.import_window and ((import_process := self.import_window.importer.import_process) and import_process.is_alive()):
            print(f'Attempting to terminate import process (PID {import_process.pid})...')
            import_process.terminate()
            cleanup_intermediate_dir(self.output_dir_path)

    def add_song_to_recently_opened(self, dir_path: Optional[str] = None, reset_menu_bars: bool = True) -> None:
        dir_path = os.path.abspath(os.path.expanduser(dir_path or self.input_dir_path))
        if not dir_path:
            return
        
        recently_opened = self.settings.value(RECENTLY_OPENED_SETTING_KEY, [], 'QStringList')
        if dir_path in recently_opened:
            recently_opened.remove(dir_path)
        recently_opened.insert(0, dir_path)
        if len(recently_opened) > self.MAX_RECENTLY_OPENED_SONGS:
            recently_opened = recently_opened[:self.MAX_RECENTLY_OPENED_SONGS]
        
        self.settings.setValue(RECENTLY_OPENED_SETTING_KEY, recently_opened)
        self.settings.sync()
        if reset_menu_bars:
            self.reset_all_menu_bars()

    def show_track_explorer_window(self, source_file_path: Optional[str] = None, input_dir_path: Optional[str] = None,
                                   show_success_message: bool = True) -> None:
        # The isolated tracks are in a subdirectory of self.output_dir_path named for the song title.
        if source_file_path:
            song_title = os.path.splitext(os.path.basename(source_file_path))[0]
            dir_path = str(os.path.join(self.output_dir_path, song_title))
        else:
            dir_path = input_dir_path or self.input_dir_path
        
        dir_path = os.path.abspath(os.path.expanduser(dir_path))
        if dir_path in self.track_windows:
            self.track_windows[dir_path].bring_to_front()
            return

        window = UnmixerTrackExplorerWindow(self, input_dir_path=dir_path, source_file_path=source_file_path,
                                            other_track_name=self.other_track_name)
        window.show()
        self.track_windows[dir_path] = window
        self.add_song_to_recently_opened(dir_path, reset_menu_bars=False)

        if show_success_message:
            QMessageBox.information(window, SUCCESS_MESSAGE_TITLE, f'Successfully wrote isolated tracks to {dir_path}.')

        if self.import_window:
            if self.import_window.importer.import_process is None:
                self.import_window.reset()
            else:
                self.import_window.reset_menu_bar()

        for window in self.track_windows.values():
            window.reset_menu_bar()

    def bring_import_window_to_front(self) -> None:
        if not self.import_window:
            self.import_window = UnmixerImportWindow(self, output_dir_path=self.output_dir_path)
            self.import_window.show()
        self.import_window.bring_to_front()

    def reset_all_menu_bars(self) -> None:
        if self.import_window:
            self.import_window.reset_menu_bar()

        for window in self.track_windows.values():
            window.reset_menu_bar()
