"""Operator preview for still images and frames from the shared video sink."""

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QColor, QImage, QPainter, QPixmap
from PyQt6.QtMultimedia import QVideoFrame
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from styles import THEME_PALETTES


class _PreviewCanvas(QWidget):
    """Paint original media at the current viewport size, with letterboxing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.media = None
        self.placeholder = "No media selected"
        self.placeholder_color = QColor("#94a3b8")
        self.setMinimumSize(160, 90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.badges = []
        self.badge_layout = QVBoxLayout(self)
        self.badge_layout.setContentsMargins(16, 16, 16, 16)
        self.badge_layout.setSpacing(8)
        self.badge_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def add_badge(self):
        label = QLabel(self)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.badges.append(label)
        self.badge_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignLeft)
        return label

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_badges()

    def showEvent(self, event):
        super().showEvent(event)
        self.fit_badges()

    def fit_badges(self):
        for label in self.badges:
            label.ensurePolished()
            natural_width = label.fontMetrics().horizontalAdvance(label.text()) + 28
            available_width = max(1, self.width() - 32)
            label.setWordWrap(natural_width > available_width)
            label.setFixedWidth(min(natural_width, available_width))

    def sizeHint(self):
        return QSize(640, 360)

    def set_media(self, media=None, placeholder=""):
        self.media = media
        self.placeholder = placeholder
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#000000"))
        if self.media is not None and not self.media.isNull():
            size = self.media.size().scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio
            )
            target = QRect(0, 0, size.width(), size.height())
            target.moveCenter(self.rect().center())
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            if isinstance(self.media, QPixmap):
                painter.drawPixmap(target, self.media)
            else:
                painter.drawImage(target, self.media)
        elif self.placeholder:
            painter.setPen(self.placeholder_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder)
        painter.end()


class PreviewWidget(QWidget):
    """Mirror images and QVideoFrame output without owning another media player."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self.mode = "blank"
        self.theme_name = "Obsidian Neon"
        self._is_projecting = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.display_label = _PreviewCanvas(self)
        layout.addWidget(self.display_label, 1)

        self.projector_status_label = self.display_label.add_badge()

        self.slideshow_status_label = self.display_label.add_badge()
        self.set_projector_status(False)
        self.set_slideshow_status(False)

    def set_image(self, media_item):
        self.current_item = media_item
        self.mode = "image"
        pixmap = QPixmap(media_item.path)
        self.display_label.set_media(
            None if pixmap.isNull() else pixmap, "Unable to load image"
        )

    def set_video(self, media_item):
        self.current_item = media_item
        self.mode = "video"
        self.display_label.set_media(placeholder="Loading video...")

    def update_video_frame(self, frame):
        if self.mode != "video":
            return
        if isinstance(frame, QVideoFrame):
            if not frame.isValid():
                return
            image = frame.toImage()
        elif isinstance(frame, QImage):
            image = frame
        else:
            return
        if not image.isNull():
            # Own the pixels after the multimedia engine releases its frame buffer.
            self.display_label.set_media(image.copy())

    def set_projector_status(self, is_projecting: bool, name="Monitor", resolution=""):
        self._is_projecting = is_projecting
        state = "ON AIR" if is_projecting else "OFF AIR • LOCAL PREVIEW"
        detail = " • ".join(value for value in (name, resolution) if value)
        self.projector_status_label.setText(f"{state} • {detail}" if detail else state)
        self._update_badge_styles()

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Obsidian Neon"])
        self.display_label.placeholder_color = QColor(palette["text_secondary"])
        self._update_badge_styles()
        self.display_label.update()

    def _update_badge_styles(self):
        neutral = self.theme_name == "Dark Gray"
        color = "#34d399" if self._is_projecting else ("#d0d0d0" if neutral else "#cbd5e1")
        background = "rgba(44, 44, 44, 220)" if neutral else (
            "rgba(6, 78, 59, 220)" if self._is_projecting else "rgba(15, 23, 42, 220)"
        )
        border = "rgba(52, 211, 153, 150)" if self._is_projecting else (
            "rgba(160, 160, 160, 100)" if neutral else "rgba(148, 163, 184, 100)"
        )
        self.projector_status_label.setStyleSheet(f"""
            color: {color}; background-color: {background};
            border: 1px solid {border}; border-radius: 14px;
            padding: 6px 12px; font-family: 'Segoe UI'; font-size: 10px; font-weight: 600;
        """)
        slideshow_color = "#e0e0e0" if neutral else "#7dd3fc"
        slideshow_background = "rgba(44, 44, 44, 220)" if neutral else "rgba(8, 47, 73, 220)"
        slideshow_border = "rgba(160, 160, 160, 150)" if neutral else "rgba(56, 189, 248, 150)"
        self.slideshow_status_label.setStyleSheet(f"""
            color: {slideshow_color}; background-color: {slideshow_background};
            border: 1px solid {slideshow_border}; border-radius: 14px;
            padding: 6px 12px; font-family: 'Segoe UI'; font-size: 10px; font-weight: 600;
        """)
        self.display_label.fit_badges()

    def set_slideshow_status(self, is_running: bool, info=""):
        self.slideshow_status_label.setText(info or ("SLIDESHOW ACTIVE" if is_running else ""))
        self.slideshow_status_label.setVisible(is_running)
        self.display_label.fit_badges()

    def clear(self):
        self.current_item = None
        self.mode = "blank"
        self.display_label.set_media(placeholder="No media selected")
