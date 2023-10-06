from typing import Optional
import random

from PyQt6.QtCore import QLineF, QRectF, Qt
from PyQt6.QtGui import QColor, QGradient, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget
from soundfile import SoundFile
import numpy as np


WAVEFORM_BACKGROUND_COLORS = [
    (QColor(20, 80, 200), QColor(90, 180, 240)),    # blue   (bass)
    (QColor(5, 175, 30), QColor(100, 240, 120)),    # green  (drums)
    (QColor(230, 30, 15), QColor(240, 110, 100)),   # red    (other/guitar/piano)
    (QColor(245, 225, 10), QColor(235, 240, 150)),  # yellow (vocals)
    (QColor(245, 90, 10), QColor(250, 150, 100)),   # orange
    (QColor(100, 5, 175), QColor(155, 55, 245)),    # purple
]


# Reference: https://gist.github.com/SpotlightKid/33ed933944beed851697039142613d98
class Waveform(QWidget):
    
    FOREGROUND_COLOR = QColor('white')
    WAVEFORM_COLOR = QColor(40, 40, 40)  # dark gray
    DISABLED_WAVEFORM_OVERLAY_COLOR = QColor(200, 200, 200, 200)  # transparent gray

    def __init__(self, sound_file: SoundFile, background_colors: Optional[tuple[QColor, QColor]] = None) -> None:
        super().__init__()
        if background_colors is None:
            background_colors = random.choice(WAVEFORM_BACKGROUND_COLORS)
        self.disabled = False
        self.frames = sound_file.read()
        self.channels = sound_file.channels
        self.sample_rate = sound_file.samplerate

        self.background_gradient = QLinearGradient()
        self.background_gradient.setColorAt(0, background_colors[0])
        self.background_gradient.setColorAt(1, background_colors[1])
        self.background_gradient.setSpread(QGradient.Spread.ReflectSpread)

    def paintEvent(self, event) -> None:
        painter = QPainter()
        painter.begin(self)
        self.draw_waveform(painter)
        painter.end()

    def draw_waveform(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = painter.device().height()
        width = painter.device().width()
        x_axis = height / 2
        samples_per_pixel = len(self.frames) / width

        # Draw background.
        self.background_gradient.setStart(0, x_axis)
        self.background_gradient.setFinalStop(0, 0)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height), 10, 10)
        pen = painter.pen()
        pen.setColor(self.FOREGROUND_COLOR)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.fillPath(path, self.background_gradient)
        painter.drawPath(path)

        # Draw waveform.
        pen.setColor(self.WAVEFORM_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(width):
            if 0 <= (start := round(x * samples_per_pixel)) < len(self.frames):
                end = max(start + 1, start + int(samples_per_pixel))
                values = self.frames[start:end]
                if (max_value := np.max(values)) > 0:
                    y = x_axis - (x_axis * max_value)
                    painter.drawLine(QLineF(x, x_axis, x, y))
                if (min_value := np.min(values)) < 0:
                    y = x_axis - (x_axis * min_value)
                    painter.drawLine(QLineF(x, x_axis, x, y))

        # Draw center line (x-axis).
        pen.setColor(self.FOREGROUND_COLOR)
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.drawLine(QLineF(0, x_axis, width, x_axis))

        # Draw gray transparent overlay if track is disabled.
        if self.disabled:
            painter.fillPath(path, self.DISABLED_WAVEFORM_OVERLAY_COLOR)

    def enable(self) -> None:
        self.disabled = False
        self.update()

    def disable(self) -> None:
        self.disabled = True
        self.update()
