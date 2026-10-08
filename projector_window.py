"""
projector_window.py - High-performance presentation window for the secondary display.
Renders both high-resolution images and live video frames seamlessly via hardware-accelerated
QPainter onto a pitch-black fullscreen canvas with strict aspect-ratio preservation.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPixmap, QImage, QColor, QScreen, QKeyEvent
from PyQt6.QtMultimedia import QVideoFrame
from media_manager import MediaItem
from typing import Optional


class ProjectorWindow(QWidget):
    """
    Borderless fullscreen presentation window displayed on the target monitor.
    Uses unified direct frame rendering to eliminate Direct3D / QVideoWidget multi-monitor glitches.
    """
    close_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_screen: Optional[QScreen] = None
        self.current_item: Optional[MediaItem] = None

        self.mode: str = 'blank'  # 'image', 'video', 'blank'
        self._pixmap: Optional[QPixmap] = None
        self._video_frame_img: Optional[QImage] = None

        self._init_ui()

    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background-color: #000000; border: none;")

        # Hide cursor on projector screen for a pristine audience experience
        self.setCursor(Qt.CursorShape.BlankCursor)

    def show_on_screen(self, screen: QScreen):
        """Place and open fullscreen on the designated screen."""
        self.target_screen = screen
        self.setScreen(screen)
        geom = screen.geometry()
        self.setGeometry(geom)
        self.showFullScreen()
        self.raise_()

    def display_image(self, item: MediaItem):
        """Display an image with smooth aspect-ratio preservation."""
        self.current_item = item
        self.mode = 'image'
        self._video_frame_img = None
        pix = QPixmap(item.path)
        self._pixmap = pix if not pix.isNull() else None
        self.update()

    def prepare_for_video(self, item: MediaItem):
        """Prepare presentation canvas for incoming video frames."""
        self.current_item = item
        self.mode = 'video'
        self._pixmap = None
        self._video_frame_img = None
        self.update()

    def update_video_frame(self, frame: QVideoFrame):
        """Receive and render live video frame from the multimedia engine."""
        if self.mode != 'video' or not frame.isValid():
            return
        img = frame.toImage()
        if not img.isNull():
            self._video_frame_img = img
            self.update()

    def show_blank(self):
        """Black out presentation screen."""
        self.current_item = None
        self.mode = 'blank'
        self._pixmap = None
        self._video_frame_img = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        if self.mode == 'image' and self._pixmap and not self._pixmap.isNull():
            pw = self._pixmap.width()
            ph = self._pixmap.height()
            draw_rect = self._calc_aspect_rect(w, h, pw, ph)
            painter.drawPixmap(draw_rect, self._pixmap)

        elif self.mode == 'video' and self._video_frame_img and not self._video_frame_img.isNull():
            fw = self._video_frame_img.width()
            fh = self._video_frame_img.height()
            draw_rect = self._calc_aspect_rect(w, h, fw, fh)
            painter.drawImage(draw_rect, self._video_frame_img)

        painter.end()

    def _calc_aspect_rect(self, container_w: int, container_h: int, media_w: int, media_h: int) -> QRect:
        if media_w <= 0 or media_h <= 0 or container_w <= 0 or container_h <= 0:
            return self.rect()

        c_ratio = container_w / container_h
        m_ratio = media_w / media_h

        if m_ratio > c_ratio:
            draw_w = container_w
            draw_h = int(draw_w / m_ratio)
            draw_x = 0
            draw_y = (container_h - draw_h) // 2
        else:
            draw_h = container_h
            draw_w = int(draw_h * m_ratio)
            draw_y = 0
            draw_x = (container_w - draw_w) // 2

        return QRect(draw_x, draw_y, draw_w, draw_h)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close_requested.emit()
            event.accept()
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Space, Qt.Key.Key_PageDown):
            self.next_requested.emit()
            event.accept()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self.prev_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)
