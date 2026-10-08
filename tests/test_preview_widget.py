"""Regression checks for preview rendering and its main-window integration."""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QImage, QPalette, QFontDatabase
from PyQt6.QtMultimedia import QVideoFrame
from PyQt6.QtWidgets import QApplication, QFrame, QLabel

from media_manager import MediaItem
from presenter_app import PresenterApp
from preview_widget import PreviewWidget
from styles import get_theme_qss


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font_path = Path("C:/Windows/Fonts/segoeui.ttf")
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
        cls.settings_dir = tempfile.TemporaryDirectory()
        QSettings.setPath(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope,
            cls.settings_dir.name,
        )
        # The explicit organization/application constructor otherwise uses the
        # Windows registry, regardless of QSettings.setDefaultFormat().
        cls.settings_patch = patch(
            "presenter_app.QSettings",
            side_effect=lambda organization, application: QSettings(
                QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                organization, application,
            ),
        )
        cls.settings_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.settings_patch.stop()
        cls.settings_dir.cleanup()

    def setUp(self):
        self.original_stylesheet = self.app.styleSheet()
        self.app.setStyleSheet(get_theme_qss("Obsidian Neon"))
        self.widget = PreviewWidget()

    def tearDown(self):
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()
        self.app.setStyleSheet(self.original_stylesheet)

    def test_status_and_clear_contract(self):
        self.widget.set_projector_status(True, "Projector", "1920x1080")
        self.assertEqual(
            self.widget.projector_status_label.text(), "ON AIR • Projector • 1920x1080"
        )
        self.widget.set_slideshow_status(True, "SLIDESHOW ACTIVE • 5s (Sequential)")
        self.assertFalse(self.widget.slideshow_status_label.isHidden())
        self.widget.clear()
        self.assertIsNone(self.widget.display_label.media)
        self.assertIn("ON AIR", self.widget.projector_status_label.text())
        self.widget.set_slideshow_status(False)
        self.assertTrue(self.widget.slideshow_status_label.isHidden())

    def test_video_frames_and_stale_frame_guard(self):
        self.widget.set_video(MediaItem(str(PROJECT_DIR / "sample_media/sample3_animation.mp4")))
        image = QImage(160, 90, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        self.widget.update_video_frame(QVideoFrame(image))
        self.assertEqual(self.widget.display_label.media.pixelColor(80, 45), QColor("red"))
        self.widget.update_video_frame(QVideoFrame())
        self.assertFalse(self.widget.display_label.media.isNull())
        self.widget.set_image(MediaItem(str(PROJECT_DIR / "sample_media/sample1_sunset.jpg")))
        still = self.widget.display_label.media
        self.widget.update_video_frame(QVideoFrame(image))
        self.assertIs(self.widget.display_label.media, still)
        self.widget.clear()
        self.widget.update_video_frame(image)
        self.assertIsNone(self.widget.display_label.media)

    def test_letterboxing_and_resize_preserve_source(self):
        self.widget.set_video(MediaItem("test.mp4"))
        image = QImage(200, 100, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        self.widget.update_video_frame(image)
        canvas = self.widget.display_label
        canvas.setFixedSize(300, 300)
        screenshot = canvas.grab().toImage()
        self.assertEqual(screenshot.pixelColor(150, 10), QColor("black"))
        self.assertEqual(screenshot.pixelColor(150, 150), QColor("red"))
        canvas.setFixedSize(400, 200)
        screenshot = canvas.grab().toImage()
        self.assertEqual(screenshot.pixelColor(200, 10), QColor("red"))
        self.assertEqual(canvas.media.size(), image.size())

    def test_missing_image_clears_previous_content(self):
        self.widget.set_image(MediaItem(str(PROJECT_DIR / "sample_media/sample1_sunset.jpg")))
        self.widget.set_image(MediaItem("missing-image.png"))
        self.assertIsNone(self.widget.display_label.media)
        self.assertEqual(self.widget.display_label.placeholder, "Unable to load image")

    def test_main_window_and_real_video_sink(self):
        window = PresenterApp()
        try:
            self.assertGreater(window.media_mgr.count(), 0)
            window.on_nav_next()
            window.start_slideshow()
            self.assertFalse(window.preview_widget.slideshow_status_label.isHidden())
            window.pause_slideshow()
            window.audio_output.setMuted(True)
            window.display_item(MediaItem(str(PROJECT_DIR / "sample_media/sample3_animation.mp4")))
            deadline = time.monotonic() + 10
            while window.preview_widget.display_label.media is None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertIsInstance(window.preview_widget.display_label.media, QImage)
            self.assertFalse(window.preview_widget.display_label.media.isNull())
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_dark_gray_theme_mute_width_and_single_timer(self):
        window = PresenterApp()
        try:
            window.theme_combo.setCurrentText("Dark Gray")
            window.show()
            self.app.processEvents()
            self.assertEqual(window.current_theme, "Dark Gray")
            self.assertEqual(window.preview_widget.theme_name, "Dark Gray")
            for frame in (
                window, window.transport_frame,
                window.findChild(QFrame, "MetadataFrame"),
                window.findChild(QFrame, "MasterDeck"),
                window.findChild(QFrame, "HeaderCard"),
                window.chip_all,
            ):
                color = frame.palette().color(QPalette.ColorRole.Window)
                self.assertEqual(color.red(), color.green())
                self.assertEqual(color.green(), color.blue())
            self.assertNotIn("#1d4ed8", self.app.styleSheet())
            self.assertIn("rgba(44, 44, 44, 220)", window.preview_widget.slideshow_status_label.styleSheet())
            window.audio_output.setMuted(False)
            window.toggle_mute()
            self.app.processEvents()
            self.assertEqual(window.mute_btn.text(), "Unmute")
            self.assertGreaterEqual(window.mute_btn.width(), window.mute_btn.sizeHint().width())
            self.assertFalse(hasattr(window.preview_widget, "time_label"))
            self.assertFalse(any(label.text().startswith("Time:") for label in window.preview_widget.findChildren(QLabel)))
            window._update_time_label(65000, 120000)
            self.assertEqual(window.time_label.text(), "01:05 / 02:00")
            window.preview_widget.set_slideshow_status(True, "SLIDESHOW ACTIVE • 5s (Sequential)")
            self.app.processEvents()
            window.grab().save(str(PROJECT_DIR / "build/dark-gray-preview.png"))
            window.theme_combo.setCurrentText("Midnight Studio")
            self.assertEqual(window.preview_widget.theme_name, "Midnight Studio")
            self.assertIn("rgba(8, 47, 73, 220)", window.preview_widget.slideshow_status_label.styleSheet())
        finally:
            # Keep following tests independent of this window's preferences.
            window._save_settings = lambda: None
            window.close()
            window.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
