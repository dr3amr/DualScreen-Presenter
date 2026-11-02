"""Regression checks for preview rendering and its main-window integration."""

import os
import sys
import tempfile
import time
import unittest
import wave
import shutil
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QImage, QPalette, QFontDatabase
from PyQt6.QtMultimedia import QVideoFrame, QMediaPlayer
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
            window.media_mgr.jump_to_index(2)
            window.start_projecting()
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
            self.assertEqual(window.mute_btn.text(), "")
            self.assertEqual(window.mute_btn.accessibleName(), "Unmute")
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

    def test_slideshow_music_lifecycle_and_looping(self):
        window = PresenterApp()
        try:
            window.random_chk.setChecked(False)
            window.display_item(window.media_mgr.jump_to_index(0))
            with tempfile.TemporaryDirectory() as directory:
                path = str(Path(directory) / "background.wav")
                with wave.open(path, "wb") as audio:
                    audio.setnchannels(1)
                    audio.setsampwidth(2)
                    audio.setframerate(8000)
                    audio.writeframes(b"\0\0" * 2400)
                window.music_start_chk.setChecked(False)
                with patch("presenter_app.QFileDialog.getOpenFileName", return_value=(path, "")):
                    window.music_browse_btn.click()
                self.assertEqual(window.music_path, path)
                self.assertEqual(window.music_path_lbl.text(), "background.wav")
                window.start_slideshow()
                self.assertNotEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.music_start_chk.setChecked(True)
                positions = []
                window.music_player.positionChanged.connect(positions.append)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    self.app.processEvents()
                    if any(b < a for a, b in zip(positions, positions[1:])):
                        break
                    time.sleep(0.01)
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                self.assertTrue(any(b < a for a, b in zip(positions, positions[1:])), positions)
                window.on_nav_next()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                # Image -> video -> image, including controls changed on video.
                position = window.music_player.position()
                window.on_nav_next()
                self.assertTrue(window.media_mgr.get_current_item().is_video)
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                self.assertEqual(window.music_player.position(), position)
                window.music_start_chk.setChecked(False)
                window.music_start_chk.setChecked(True)
                window.pause_slideshow()
                window.start_slideshow()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                window.on_nav_next()
                self.assertTrue(window.media_mgr.get_current_item().is_image)
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.on_nav_back()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                window.on_nav_next()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.vol_slider.setValue(42)
                self.assertAlmostEqual(window.music_audio_output.volume(), 0.42, places=4)
                window.audio_output.setMuted(False)
                window.toggle_mute()
                self.assertTrue(window.music_audio_output.isMuted())
                window.vol_slider.setValue(43)
                self.assertFalse(window.music_audio_output.isMuted())
                window.pause_slideshow()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                window.start_slideshow()
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.music_start_chk.setChecked(False)
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                window.music_start_chk.setChecked(True)
                window.stop_projecting()
                self.assertFalse(window.slideshow_running)
                self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
                window.music_clear_btn.click()
                self.assertTrue(window.music_player.source().isEmpty())
                self.assertEqual(window.music_path, "")
                window._set_music_file(str(Path(directory) / "missing.mp3"))
                window.start_slideshow()
                self.assertIn("unavailable", window.music_path_lbl.text())
                self.assertTrue(window.slideshow_running)
        finally:
            window._save_settings = lambda: None
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_music_settings_and_themed_control_icons(self):
        window = PresenterApp()
        restored = None
        try:
            window._set_music_file(str(PROJECT_DIR / "remembered.mp3"))
            window.music_start_chk.setChecked(False)
            window._save_settings()
            restored = PresenterApp()
            self.assertEqual(restored.music_path, window.music_path)
            self.assertFalse(restored.music_start_chk.isChecked())
            with patch("presenter_app.QFileDialog.getOpenFileName", return_value=("", "")):
                restored.on_browse_music()
            self.assertEqual(restored.music_path, window.music_path)
            for theme in ("Obsidian Neon", "Midnight Studio", "Cyberpunk Amber", "Slate Graphite", "Dark Gray"):
                restored.on_theme_changed(theme)
                for button in (restored.back_btn, restored.next_btn, restored.mute_btn, restored.refresh_screens_btn, restored.play_pause_btn, restored.video_stop_btn):
                    self.assertFalse(button.icon().isNull())
                    self.assertEqual(button.text(), "")
                    self.assertTrue(button.accessibleName())
                    self.assertTrue(button.toolTip())
            before = restored.mute_btn.icon().pixmap(18, 18).toImage()
            restored.toggle_mute()
            self.assertNotEqual(before, restored.mute_btn.icon().pixmap(18, 18).toImage())
        finally:
            for item in (window, restored):
                if item:
                    item._save_settings = lambda: None
                    item.close()
                    item.deleteLater()
            self.app.processEvents()

    def test_offline_slideshow_plays_videos_and_advances_after_end(self):
        with patch.object(PresenterApp, "_load_settings", lambda window: window.load_folder(str(PROJECT_DIR / "sample_media"))):
            window = PresenterApp()
        try:
            window._save_settings = lambda: None
            window.random_chk.setChecked(False)
            window.video_wait_chk.setChecked(True)
            window.audio_output.setMuted(True)
            window.display_item(window.media_mgr.jump_to_index(1))
            window.start_slideshow()
            # Entering a video from an image must autoplay without a projector.
            window.on_nav_next()
            self.assertTrue(window.media_mgr.get_current_item().is_video)
            self.assertFalse(window.is_projecting)
            self.assertIsNone(window.projector_window)
            deadline = time.monotonic() + 5
            while window.player.position() < 250 and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertGreater(window.player.position(), 0)
            self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
            self.assertIsInstance(window.preview_widget.display_label.media, QImage)
            window._slideshow_remaining_ms = 100
            window._on_slideshow_tick()
            self.assertTrue(window.media_mgr.get_current_item().is_video)
            # Exercise the real end-of-media signal and automatic next slide.
            window.player.setPosition(window.player.duration() - 200)
            deadline = time.monotonic() + 5
            while window.media_mgr.get_current_item().is_video and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertTrue(window.media_mgr.get_current_item().is_image)
            window.pause_slideshow()
            window.display_item(window.media_mgr.jump_to_index(2))
            self.assertNotEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
            # Starting on an already selected video must also autoplay.
            window.start_slideshow()
            deadline = time.monotonic() + 5
            while window.player.position() < 250 and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertGreater(window.player.position(), 0)
            self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
            opening_frame = window._video_start_frame.copy()
            window.slideshow_toggle_btn.click()
            self.assertFalse(window.slideshow_running)
            self.assertFalse(window.slideshow_timer.isActive())
            self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
            self.assertEqual(window.player.position(), 0)
            self.assertEqual(window.preview_widget.display_label.media, opening_frame)
            self.assertEqual(window.play_pause_btn.accessibleName(), "Play video")
            window.slideshow_toggle_btn.click()
            self.assertTrue(window.slideshow_running)
            self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
            # With waiting disabled, the normal interval advances the video.
            window.video_wait_chk.setChecked(False)
            window._slideshow_remaining_ms = 100
            window._on_slideshow_tick()
            self.assertTrue(window.media_mgr.get_current_item().is_image)
        finally:
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_projecting_restarts_video_from_running_offline_slideshow(self):
        for autostart in (False, True):
            with self.subTest(autostart=autostart):
                with patch.object(PresenterApp, "_load_settings", lambda window: window.load_folder(str(PROJECT_DIR / "sample_media"))):
                    window = PresenterApp()
                try:
                    window._save_settings = lambda: None
                    window.audio_output.setMuted(True)
                    window.random_chk.setChecked(False)
                    window.autostart_chk.setChecked(autostart)
                    window.display_item(window.media_mgr.jump_to_index(2))
                    window.start_slideshow()
                    deadline = time.monotonic() + 5
                    while window.player.position() < 500 and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                    self.assertGreaterEqual(window.player.position(), 500)
                    self.assertFalse(window.is_projecting)
                    window._slideshow_remaining_ms = 100
                    window.start_proj_btn.click()
                    self.assertTrue(window.is_projecting)
                    self.assertTrue(window.slideshow_running)
                    self.assertEqual(window.player.position(), 0)
                    self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                    self.assertEqual(window._slideshow_remaining_ms, window.slideshow_interval_ms)
                    deadline = time.monotonic() + 5
                    while window.player.position() < 250 and time.monotonic() < deadline:
                        self.app.processEvents()
                        time.sleep(0.01)
                    self.assertGreater(window.player.position(), 0)
                finally:
                    window.close()
                    window.deleteLater()
                    self.app.processEvents()

    def test_projecting_restarts_offline_music_on_images_and_videos(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "background.wav")
            with wave.open(path, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 24000)
            for video_slide in (False, True):
                with self.subTest(video_slide=video_slide):
                    with patch.object(PresenterApp, "_load_settings", lambda window: window.load_folder(str(PROJECT_DIR / "sample_media"))):
                        window = PresenterApp()
                    try:
                        window._save_settings = lambda: None
                        window.audio_output.setMuted(True)
                        window.music_start_chk.setChecked(True)
                        window._set_music_file(path)
                        window.start_slideshow()
                        deadline = time.monotonic() + 5
                        while window.music_player.position() < 250 and time.monotonic() < deadline:
                            self.app.processEvents()
                            time.sleep(0.01)
                        self.assertGreater(window.music_player.position(), 0)
                        if video_slide:
                            window.display_item(window.media_mgr.jump_to_index(2))
                            self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                        window.start_proj_btn.click()
                        self.assertEqual(window.music_player.position(), 0)
                        if video_slide:
                            self.assertNotEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                            window.on_nav_next()
                        self.assertEqual(window.music_player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                        deadline = time.monotonic() + 5
                        while window.music_player.position() < 250 and time.monotonic() < deadline:
                            self.app.processEvents()
                            time.sleep(0.01)
                        self.assertGreater(window.music_player.position(), 0)
                    finally:
                        window.close()
                        window.deleteLater()
                        self.app.processEvents()

    def test_video_first_startup_and_offline_paused_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            shutil.copyfile(PROJECT_DIR / "sample_media/sample3_animation.mp4", Path(directory) / "first.mp4")
            with patch.object(PresenterApp, "_load_settings", lambda window: window.load_folder(directory)):
                window = PresenterApp()
            try:
                self.assertTrue(window.media_mgr.get_current_item().is_video)
                deadline = time.monotonic() + 5
                while window.preview_widget.display_label.media is None and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.01)
                self.assertNotEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                self.assertTrue(window.play_pause_btn.isEnabled())
                self.assertEqual(window.player.position(), 0)
                self.assertIsInstance(window.preview_widget.display_label.media, QImage)
                opening_frame = window.preview_widget.display_label.media.copy()
                self.assertTrue(window.video_stop_btn.isEnabled())
                transport_layout = window.transport_frame.layout()
                self.assertLess(transport_layout.indexOf(window.video_stop_btn), transport_layout.indexOf(window.play_pause_btn))
                window.play_pause_btn.click()
                self.assertFalse(window.is_projecting)
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                deadline = time.monotonic() + 5
                while window.player.position() < 500 and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.01)
                window.play_pause_btn.click()
                self.app.processEvents()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                paused_position = window.player.position()
                paused_image = window.preview_widget.display_label.media.copy()
                deadline = time.monotonic() + 0.2
                while time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.01)
                self.assertEqual(window.player.position(), paused_position)
                self.assertEqual(window.preview_widget.display_label.media, paused_image)
                window.display_item(window.media_mgr.get_current_item())
                self.assertEqual(window.player.position(), paused_position)
                self.assertEqual(window.preview_widget.display_label.media, paused_image)
                window.video_stop_btn.click()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
                self.assertEqual(window.player.position(), 0)
                self.assertEqual(window.timeline_slider.value(), 0)
                self.assertEqual(window.preview_widget.display_label.media, opening_frame)
                self.assertEqual(window.play_pause_btn.accessibleName(), "Play video")
                window.play_pause_btn.click()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.video_stop_btn.click()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
                self.assertEqual(window.player.position(), 0)
                window.show()
                self.app.processEvents()
                window.grab().save(str(PROJECT_DIR / "build/video-stop-preview.png"))
                window.start_projecting()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                self.assertTrue(window.play_pause_btn.isEnabled())
                self.assertEqual(window.play_pause_btn.text(), "")
                self.assertEqual(window.play_pause_btn.accessibleName(), "Pause video")
                pause_icon = window.play_pause_btn.icon().pixmap(18, 18).toImage()
                window.play_pause_btn.click()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PausedState)
                self.assertEqual(window.play_pause_btn.accessibleName(), "Play video")
                self.assertNotEqual(pause_icon, window.play_pause_btn.icon().pixmap(18, 18).toImage())
                window.play_pause_btn.click()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                deadline = time.monotonic() + 5
                while window.player.position() < 300 and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.01)
                self.assertGreater(window.player.position(), 0)
                window.video_stop_btn.click()
                self.assertTrue(window.is_projecting)
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
                self.assertEqual(window.player.position(), 0)
                window.play_pause_btn.click()
                window.player.setPosition(1000)
                window.stop_projecting()
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.StoppedState)
                self.assertEqual(window.player.position(), 0)
                self.assertEqual(window.preview_widget.display_label.media, opening_frame)
                self.assertTrue(window.play_pause_btn.isEnabled())
                self.assertIsInstance(window.preview_widget.display_label.media, QImage)
                window.play_pause_btn.click()
                self.assertFalse(window.is_projecting)
                self.assertEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
                window.play_pause_btn.click()
                window.on_reload_folder()
                self.assertNotEqual(window.player.playbackState(), QMediaPlayer.PlaybackState.PlayingState)
            finally:
                window._save_settings = lambda: None
                window.close()
                window.deleteLater()
                self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
