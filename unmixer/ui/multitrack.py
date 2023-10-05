from typing import Optional
import os.path
import shutil

from PyQt6.QtCore import (
    QLine,
    QPoint,
    QPointF,
    QRect,
    Qt,
    QTimer,
    QUrl,
)
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from soundfile import SoundFile

from unmixer.constants import OTHER_TRACK_NAME
from unmixer.ui.constants import FONT_WEIGHT_BOLD, SUCCESS_MESSAGE_TITLE
from unmixer.ui.track import Track
from unmixer.ui.waveform import Waveform, WAVEFORM_BACKGROUND_COLORS


MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = MINUTES_PER_HOUR
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR


class PlaybackControls(QWidget):

    PLAYBACK_TIME_FONT_SIZE = 15
    DEFAULT_PLAYBACK_TIME_TEXT = '0:00 / 0:00'
    PLAYBACK_TIMER_INTERVAL_MILLIS = 500
    
    LAYOUT_SPACING = 50

    MIN_BUTTON_WIDTH = 90
    MIN_PLAYBACK_TIME_WIDTH = 120

    EXPORT_BUTTON_TEXT = '💾 Export...'
    PLAY_BUTTON_TEXT = '▶️ Play'
    PAUSE_BUTTON_TEXT = '⏸️ Pause'
    RESTART_BUTTON_TEXT = '⏮️ Restart'
    
    EXPORT_BUTTON_ENABLED_TOOLTIP = 'Export the selected tracks to a new file.'
    EXPORT_BUTTON_DISABLED_TOOLTIP_TEMPLATE = 'Enable 2-{n} tracks to export them as a new mix.'
    EXPORT_BUTTON_NOT_ENOUGH_TRACKS_TOOLTIP = 'There are not enough tracks to create a new mix.'

    def __init__(self, parent: 'MultiTrackDisplay') -> None:
        super().__init__()
        
        self.export_button = QPushButton(self.EXPORT_BUTTON_TEXT)
        self.export_button.setDisabled(True)  # Initially, all tracks are selected, so exporting is disabled.
        if len(parent.tracks) < 3:
            self.export_button_disabled_tooltip = self.EXPORT_BUTTON_NOT_ENOUGH_TRACKS_TOOLTIP
        else:
            self.export_button_disabled_tooltip = self.EXPORT_BUTTON_DISABLED_TOOLTIP_TEMPLATE.format(n=len(parent.tracks)-1)
        self.export_button.setToolTip(self.export_button_disabled_tooltip)
        self.export_button.setMinimumWidth(self.MIN_BUTTON_WIDTH)
        self.export_button.clicked.connect(self.export_selected_tracks)

        self.restart_button = QPushButton(self.RESTART_BUTTON_TEXT)
        self.restart_button.setMinimumWidth(self.MIN_BUTTON_WIDTH)
        self.restart_button.clicked.connect(self.restart_track)

        self.playing = False
        self.play_button = QPushButton(self.PLAY_BUTTON_TEXT)
        self.play_button.setMinimumWidth(self.MIN_BUTTON_WIDTH)
        self.play_button.clicked.connect(self.toggle_playback)

        self.playback_time = QLabel(self.DEFAULT_PLAYBACK_TIME_TEXT)
        font = self.playback_time.font()
        font.setPixelSize(self.PLAYBACK_TIME_FONT_SIZE)
        font.setWeight(FONT_WEIGHT_BOLD)
        self.playback_time.setFont(font)
        self.playback_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.playback_time.setMinimumWidth(self.MIN_PLAYBACK_TIME_WIDTH)
        self.update_playback_time_timer = QTimer(self)
        self.update_playback_time_timer.setInterval(self.PLAYBACK_TIMER_INTERVAL_MILLIS)
        self.update_playback_time_timer.timeout.connect(self.update_playback_time)
        self.update_playback_time_timer.start()

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.export_button)
        layout.addSpacing(self.LAYOUT_SPACING)
        layout.addWidget(self.restart_button)
        layout.addWidget(self.play_button)
        layout.addSpacing(self.LAYOUT_SPACING)
        layout.addWidget(self.playback_time)
        layout.addStretch()
        self.setLayout(layout)
        self.show()

    @property
    def player(self) -> QMediaPlayer:
        return self.parent().player

    @staticmethod
    def format_playback_time(time_in_millis: int) -> str:
        total_seconds = round(time_in_millis / 1000)
        hours, remaining_seconds = divmod(total_seconds, SECONDS_PER_HOUR)
        minutes, seconds = divmod(remaining_seconds, SECONDS_PER_MINUTE)
        return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'

    def update_playback_time(self) -> None:
        if self.player and self.player.isPlaying():
            current_time = self.format_playback_time(self.player.position())
            total_time = self.format_playback_time(self.player.duration())
            self.playback_time.setText(f'{current_time} / {total_time}')
            self.update()

    def toggle_playback_state(self) -> None:
        self.playing = not self.playing
        self.play_button.setText(self.PAUSE_BUTTON_TEXT if self.playing else self.PLAY_BUTTON_TEXT)
        self.update()

    def toggle_playback(self) -> None:
        if not self.play_button.isEnabled():
            return

        self.toggle_playback_state()
        if self.playing:
            self.parent().play_selected_tracks()
        else:
            self.parent().pause_playback()
        self.update()

    def restart_track(self) -> None:
        if self.player:
            if self.player.isPlaying():
                self.player.setPosition(0)
            else:
                self.parent().prev_position = 0
        self.playback_time.setText(self.DEFAULT_PLAYBACK_TIME_TEXT)
        self.update()
    
    def export_selected_tracks(self) -> None:
        self.parent().export_selected_tracks()

    def enable_export_button(self) -> None:
        self.export_button.setDisabled(False)
        self.export_button.setToolTip(self.EXPORT_BUTTON_ENABLED_TOOLTIP)

    def disable_export_button(self) -> None:
        self.export_button.setDisabled(True)
        self.export_button.setToolTip(self.export_button_disabled_tooltip)
    
    def enable_play_button(self) -> None:
        self.play_button.setDisabled(False)

    def disable_play_button(self) -> None:
        self.play_button.setDisabled(True)


class MultiTrackPlayhead(QWidget):
    
    COLOR = Waveform.FOREGROUND_COLOR
    DRAG_SCALE_FACTOR = 0.9
    PLAYHEAD_SIZE = 16
    TIMER_INTERVAL_MILLIS = 500
    
    def __init__(self, parent: 'MultiTrackDisplay') -> None:
        super().__init__(parent=parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        
        self._dragging = False
        
        self.update_playhead_timer = QTimer(self)
        self.update_playhead_timer.setInterval(self.TIMER_INTERVAL_MILLIS)
        self.update_playhead_timer.timeout.connect(self.repaint)
        self.update_playhead_timer.start()

        self.adjust_size_and_position()
        self.raise_()  # Bring the playhead to the top of the "stack" (z-axis).
        self.show()
        
    @property
    def player(self) -> QMediaPlayer:
        return self.parent().player
    
    @property
    def progress(self) -> float:
        if self.player:
            return self.player.position() / self.player.duration()
        return 0
    
    def adjust_size_and_position(self) -> None:
        x1, y1, x2, y2 = self.parent().geometry().getCoords()
        track_controls_width = self.parent().tracks[0].controls.width()
        play_controls_height = self.parent().controls.height()
        self.setGeometry(QRect(x1 - track_controls_width, y1, x2, y2 - play_controls_height))
        self.move(x1 + track_controls_width, y1)
    
    def is_mouse_event_within_playhead(self, event) -> bool:
        top_waveform = self.parent().tracks[0].waveform
        line_top = self.mapFromGlobal(top_waveform.mapToGlobal(QPoint(int(top_waveform.width() * self.progress), 0)))
        playhead_bounds = QRect(int(line_top.x() - self.PLAYHEAD_SIZE / 2), line_top.y() - self.PLAYHEAD_SIZE,
                                int(line_top.x() + self.PLAYHEAD_SIZE / 2), line_top.y())
        return playhead_bounds.contains(event.pos())
    
    def mousePressEvent(self, event):
        if self.is_mouse_event_within_playhead(event):
            self._dragging = True
            # TODO: Figure out why this isn't working (on macOS 14.0).
            QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
            QApplication.processEvents()
    
    def mouseMoveEvent(self, event):
        if not self._dragging or not self.player:
            return
        
        top_waveform = self.parent().tracks[0].waveform
        position = int((event.pos().x() / top_waveform.width()) * self.player.duration() * self.DRAG_SCALE_FACTOR)
        if self.player.isPlaying():
            self.player.setPosition(position)
        else:
            self.parent().prev_position = position
    
    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
    
    def paintEvent(self, event) -> None:
        self.adjust_size_and_position()
        painter = QPainter()
        painter.begin(self)
        self.draw_playhead(painter)
        painter.end()
    
    def draw_playhead(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = painter.pen()
        pen.setColor(self.COLOR)
        pen.setWidth(2)
        painter.setPen(pen)

        # Draw vertical line.
        top_waveform = self.parent().tracks[0].waveform
        line_top = self.mapFromGlobal(top_waveform.mapToGlobal(QPoint(int(top_waveform.width() * self.progress), 0)))
        bottom_waveform = self.parent().tracks[-1].waveform
        line_bottom = self.mapFromGlobal(bottom_waveform.mapToGlobal(QPoint(int(top_waveform.width() * self.progress),
                                                                            bottom_waveform.height())))
        painter.drawLine(QLine(line_top.x(), line_top.y(), line_bottom.x(), line_bottom.y()))
        
        # Draw triangular playhead at the top.
        triangle_path = QPainterPath()
        triangle_path.moveTo(line_top.toPointF())
        triangle_path.lineTo(QPointF(line_top.x() - self.PLAYHEAD_SIZE / 2, line_top.y() - self.PLAYHEAD_SIZE))
        triangle_path.lineTo(QPointF(line_top.x() + self.PLAYHEAD_SIZE / 2, line_top.y() - self.PLAYHEAD_SIZE))
        triangle_path.lineTo(line_top.toPointF())
        painter.fillPath(triangle_path, self.COLOR)


class MultiTrackDisplay(QWidget):
    
    DEFAULT_VOLUME = 50
    
    EXPORT_DIALOG_TITLE = 'Export Selected Tracks'
    
    TITLE_FONT_SIZE = 30
    
    def __init__(self, song_title: str, file_paths: list[str], other_track_name: Optional[str] = None) -> None:
        super().__init__()
        self._other_track_name = other_track_name
        self._soloed_track = None
        
        self.title = QLabel(f'Song:  {song_title}')
        font = self.title.font()
        font.setPixelSize(self.TITLE_FONT_SIZE)
        font.setWeight(FONT_WEIGHT_BOLD)
        self.title.setFont(font)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.audio_output = None
        self.player = None
        self.prev_position = None
        
        self.tracks = []
        for i, file_path in enumerate(file_paths):
            with SoundFile(file_path, 'rb') as sound_file:
                colors = WAVEFORM_BACKGROUND_COLORS[i % len(WAVEFORM_BACKGROUND_COLORS)]
                name = (
                    self._other_track_name.capitalize()
                    if self._other_track_name and os.path.basename(sound_file.name).lower().startswith(f'{OTHER_TRACK_NAME}.')
                    else None
                )
                self.tracks.append(Track(sound_file, colors, name=name))
                
        self.controls = PlaybackControls(self)  # This needs to be initialized AFTER self.tracks is populated!
        
        layout = QVBoxLayout()
        layout.addWidget(self.title, stretch=1)
        for track in self.tracks:
            layout.addWidget(track, stretch=3)
        layout.addWidget(self.controls, stretch=1)
        self.setLayout(layout)
        
        self.playhead = MultiTrackPlayhead(self)  # This needs to be initialized AFTER self.tracks is populated!
        
        self.setFocusProxy(self.controls.play_button)
        self.show()
    
    @property
    def selected_tracks(self) -> list[Track]:
        if self.soloed_track:
            return [self.soloed_track]
        return [track for track in self.tracks if not track.muted]
    
    @property
    def soloed_track(self) -> Optional[Track]:
        return self._soloed_track
    
    @soloed_track.setter
    def soloed_track(self, track: Optional[Track]) -> None:
        if track:
            track.enable_waveform()
            for other_track in self.tracks:
                if other_track != track:
                    if other_track == self.soloed_track:
                        other_track.controls.toggle_soloed_state()
                    other_track.disable_waveform()
        else:
            for other_track in self.tracks:
                if not other_track.muted:
                    other_track.enable_waveform()
        self._soloed_track = track
    
    @property
    def file_path_for_selected_tracks(self) -> str:
        return self.parent().temp_file_path([track.file_path for track in self.selected_tracks])
    
    def handle_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia and self.controls.playing:
            # Auto-pause at the end of the track.
            self.controls.toggle_playback_state()
    
    def init_audio(self, source_url: Optional[QUrl] = None) -> tuple[QAudioOutput, QMediaPlayer]:
        audio_output = QAudioOutput()
        audio_output.setVolume(self.DEFAULT_VOLUME)
        player = QMediaPlayer()
        player.mediaStatusChanged.connect(self.handle_media_status_changed)
        player.setAudioOutput(audio_output)
        if source_url:
            player.setSource(source_url)
        return audio_output, player
    
    def update_media_player_for_current_selected_tracks(self) -> None:
        if not self.selected_tracks or not self.controls.playing:
            return
        
        source_url = QUrl.fromLocalFile(self.file_path_for_selected_tracks)
        if not self.player or self.player.source() != source_url:
            audio_output, player = self.init_audio(source_url)
            if self.player and self.player.isPlaying():
                self.prev_position = self.player.position()
                QTimer.singleShot(0, self.player.stop)  # https://stackoverflow.com/a/49239010
            self.audio_output = audio_output
            self.player = player
        
        if self.controls.playing and not self.player.isPlaying():
            if self.prev_position is not None:
                # Seek the new track to the same position as the previous track.
                self.player.setPosition(self.prev_position)
            self.player.play()
    
    def play_selected_tracks(self) -> None:
        if self.player and self.player.isPlaying():
            return
        self.update_media_player_for_current_selected_tracks()
        self.prev_position = None
    
    def pause_playback(self) -> None:
        if self.player and self.player.isPlaying():
            self.prev_position = self.player.position()
            self.player.pause()
    
    def export_selected_tracks(self) -> None:
        # If a single track, no tracks, or all tracks are selected, then there is nothing to export.
        if len(self.selected_tracks) < 2 or len(self.selected_tracks) == len(self.tracks):
            return
        
        temp_file_path = self.file_path_for_selected_tracks
        _, extension = os.path.splitext(temp_file_path)
        export_dir = os.path.dirname(self.selected_tracks[0].file_path)
        
        names = []
        for name in sorted(os.path.splitext(os.path.basename(track.file_path))[0] for track in self.selected_tracks):
            if name.lower() == OTHER_TRACK_NAME and self._other_track_name:
                name = self._other_track_name
            names.append(name)
        
        export_name = '+'.join(names) + extension
        default_export_path = os.path.join(export_dir, export_name)
        export_path, _ = QFileDialog.getSaveFileName(self, self.EXPORT_DIALOG_TITLE, default_export_path)
        if not export_path:
            return  # User canceled or did not enter a path.
        
        if not export_path.endswith(extension):
            # Force file path to end with the correct extension.
            export_path = os.path.splitext(export_path)[0] + extension
        
        # This will overwrite the file if it exists, but the user already confirmed that they want that.
        shutil.copy(temp_file_path, export_path)
        QMessageBox.information(self, SUCCESS_MESSAGE_TITLE, f'Successfully exported {export_path}.')
