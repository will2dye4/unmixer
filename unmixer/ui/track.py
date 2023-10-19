from typing import Optional
import os.path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from soundfile import SoundFile

from unmixer.ui.constants import FONT_WEIGHT_BOLD
from unmixer.ui.waveform import Waveform


class TrackControls(QWidget):
    
    DEFAULT_TRACK_NAME_FONT_SIZE = 15
    TRACK_NAME_FONT_SIZE_REDUCTION_AMOUNT = 3
    TRACK_NAME_REDUCTION_THRESHOLD = 10
    
    MIN_BUTTON_WIDTH = 85
    
    PLUS_SEPARATOR = ' + '
    
    MUTE_BUTTON_TEXT = '⬛️ Mute'
    UNMUTE_BUTTON_TEXT = '🟥 Unmute'
    
    SOLO_BUTTON_TEXT = '⬛️ Solo'
    UNSOLO_BUTTON_TEXT = '🟨 Unsolo'
    
    def __init__(self, sound_file: SoundFile, name: Optional[str] = None) -> None:
        super().__init__()
        tooltip = None
        if name is None:
            name, tooltip = self.format_track_name(sound_file.name)
        
        self.name = QLabel(name)
        font = self.name.font()
        font_size = self.DEFAULT_TRACK_NAME_FONT_SIZE
        if len(name) > self.TRACK_NAME_REDUCTION_THRESHOLD:
            font_size -= self.TRACK_NAME_FONT_SIZE_REDUCTION_AMOUNT * (name.count(self.PLUS_SEPARATOR) or 1)
        font.setPixelSize(font_size)
        font.setWeight(FONT_WEIGHT_BOLD)
        self.name.setFont(font)
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if tooltip:
            self.setStatusTip(tooltip)
            self.setToolTip(tooltip)
        
        self.muted = False
        self.mute_button = QPushButton(self.MUTE_BUTTON_TEXT)
        self.mute_button.setStyleSheet('text-align: left')
        self.mute_button.setMinimumWidth(self.MIN_BUTTON_WIDTH)
        self.mute_button.clicked.connect(self.toggle_muted)
        
        self.soloed = False
        self.solo_button = QPushButton(self.SOLO_BUTTON_TEXT)
        self.solo_button.setStyleSheet('text-align: left')
        self.solo_button.setMinimumWidth(self.MIN_BUTTON_WIDTH)
        self.solo_button.clicked.connect(self.toggle_soloed)
        
        layout = QVBoxLayout()
        layout.addWidget(self.name)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.solo_button)
        self.setLayout(layout)
        self.show()
    
    @classmethod
    def format_track_name(cls, file_path: str) -> tuple[str, Optional[str]]:
        name, _ = os.path.splitext(os.path.basename(file_path))
        is_long_name = name.count('+') > 1
        words = []
        full_words = [] if is_long_name else None
        for word in name.split('+'):
            full_word = ' '.join(subword.capitalize() for subword in word.split('_'))
            if is_long_name:
                full_words.append(full_word)
            words.append(word[0].capitalize() if is_long_name else full_word)
        name = cls.PLUS_SEPARATOR.join(words)
        tooltip = cls.PLUS_SEPARATOR.join(full_words) if is_long_name else None
        return name, tooltip
    
    @property
    def track(self) -> 'Track':
        return self.parent()
    
    @property
    def soloed_track(self) -> Optional['Track']:
        return self.track.parent().soloed_track
    
    def toggle_muted_state(self) -> None:
        self.muted = not self.muted
        self.mute_button.setText(self.UNMUTE_BUTTON_TEXT if self.muted else self.MUTE_BUTTON_TEXT)
        self.update()
    
    def toggle_muted(self) -> None:
        if self.soloed:
            return
        self.toggle_muted_state()
        self.track.waveform.disabled = self.muted or (self.soloed_track is not None and self.soloed_track != self.track)
        if selected_count := len(self.track.parent().selected_tracks):
            self.track.parent().controls.enable_play_button()
            if selected_count == 1 or selected_count == len(self.track.parent().tracks):
                self.track.parent().controls.disable_export_button()
            else:
                self.track.parent().controls.enable_export_button()
        else:
            self.track.parent().controls.disable_export_button()
            self.track.parent().controls.disable_play_button()
            if self.track.parent().controls.playing:
                # Auto-pause if all tracks are muted.
                self.track.parent().pause_playback()
        self.track.parent().update_media_player_for_current_selected_tracks()
        self.track.parent().update()
    
    def toggle_soloed_state(self) -> None:
        self.soloed = not self.soloed
        self.solo_button.setText(self.UNSOLO_BUTTON_TEXT if self.soloed else self.SOLO_BUTTON_TEXT)
        if self.soloed and self.muted:
            self.toggle_muted_state()
        self.mute_button.setDisabled(self.soloed)
        self.update()
    
    def toggle_soloed(self) -> None:
        self.toggle_soloed_state()
        self.parent().parent().soloed_track = self.track if self.soloed else None
        if self.soloed:
            self.track.parent().controls.enable_play_button()
            self.track.parent().controls.disable_export_button()
        elif 1 < len(self.track.parent().selected_tracks) < len(self.track.parent().tracks):
            self.track.parent().controls.enable_export_button()
        self.track.parent().update_media_player_for_current_selected_tracks()
        self.track.parent().update()


class Track(QWidget):
    
    def __init__(self, sound_file: SoundFile, background_colors: Optional[tuple[QColor, QColor]] = None,
                 name: Optional[str] = None) -> None:
        super().__init__()
        self.file_path = sound_file.name
        self.controls = TrackControls(sound_file, name=name)
        self.waveform = Waveform(sound_file, background_colors)
        self.waveform.setStatusTip(self.controls.statusTip())
        self.waveform.setToolTip(self.controls.toolTip())
        
        layout = QHBoxLayout()
        layout.addWidget(self.controls, stretch=1)
        layout.addWidget(self.waveform, stretch=9)
        self.setLayout(layout)
        self.show()
    
    @property
    def muted(self) -> bool:
        return self.controls.muted
    
    @property
    def soloed(self) -> bool:
        return self.controls.soloed
    
    def enable_waveform(self) -> None:
        self.waveform.enable()
        
    def disable_waveform(self) -> None:
        self.waveform.disable()
