"""
presenter_app.py - Main operator control window for DualScreen Presenter — Broadcast Console.
Orchestrates secondary monitor projection, timed slideshow automation with selectable intervals,
randomized navigation mode via checkbox, multi-theme customization, master audio volume,
and synchronized live preview with clean icon-free compact buttons.
"""

import os
import sys
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QListWidget, QListWidgetItem, QFileDialog,
    QLineEdit, QFrame, QCheckBox, QSplitter, QProgressBar, QMessageBox,
    QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, QSettings, QPointF
from PyQt6.QtGui import (
    QGuiApplication, QScreen, QIcon, QKeySequence, QShortcut,
    QColor, QDragEnterEvent, QDropEvent, QPixmap, QPainter, QPen, QPolygonF
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink

from media_manager import MediaManager, MediaItem
from projector_window import ProjectorWindow
from preview_widget import PreviewWidget
from styles import get_theme_qss, AVAILABLE_THEMES, THEME_PALETTES


def _to_bool(val) -> bool:
    """Safely coerce a QSettings value (may be str/bool/int) to Python bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'yes')
    return bool(val)


def _media_type_icon(is_video: bool, color: QColor) -> QIcon:
    """Draw crisp photo and film icons without external assets or emoji fonts."""
    pixmap = QPixmap(72, 72)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(3, 3)
    painter.setPen(QPen(color, 1.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if is_video:
        painter.drawRoundedRect(2, 3, 20, 18, 2, 2)
        painter.drawLine(6, 3, 6, 21)
        painter.drawLine(18, 3, 18, 21)
        for y in (7, 12, 17):
            painter.drawLine(2, y, 6, y)
            painter.drawLine(18, y, 22, y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([
            QPointF(10, 8), QPointF(10, 16), QPointF(16, 12),
        ]))
    else:
        painter.drawRoundedRect(2, 3, 20, 18, 2, 2)
        painter.drawEllipse(QPointF(16.5, 8), 1.5, 1.5)
        painter.drawPolyline(QPolygonF([
            QPointF(3, 18), QPointF(8, 11), QPointF(13, 17),
            QPointF(16, 13), QPointF(21, 19),
        ]))
    painter.end()
    return QIcon(pixmap)


class PresenterApp(QMainWindow):
    """Main window with presentation control deck, slideshow engine, and live preview."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DualScreen Presenter — Broadcast Console")
        self.resize(1180, 780)
        self.setMinimumSize(960, 640)

        # Allow dragging and dropping folders or media directly onto the window
        self.setAcceptDrops(True)

        # Core logic
        self.media_mgr = MediaManager()
        self.is_projecting = False
        self.projector_window: Optional[ProjectorWindow] = None
        self._is_scrubbing = False
        self._last_volume = 75
        self.current_theme = "Obsidian Neon"
        self._media_type_icons = {}

        # Slideshow Engine State
        self.slideshow_running = False
        self.slideshow_interval_ms = 5000  # Default 5 seconds
        self._slideshow_remaining_ms = 5000
        self.slideshow_timer = QTimer(self)
        self.slideshow_timer.setInterval(100)  # 100ms resolution for smooth progress countdown
        self.slideshow_timer.timeout.connect(self._on_slideshow_tick)

        # Unified Multimedia Engine
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(self._last_volume / 100.0)

        # Single centralized video sink feeds BOTH preview monitor and secondary projector
        self.video_sink = QVideoSink(self)
        self.player.setVideoSink(self.video_sink)
        self.video_sink.videoFrameChanged.connect(self._on_video_frame)

        # Build UI & Connect signals
        self._init_ui()
        self._init_shortcuts()
        self._connect_player_signals()

        # Populate monitor list, then restore all persisted settings
        self.refresh_screens()
        self._load_settings()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 10)
        main_layout.setSpacing(8)

        # 1. TOP HEADER BAR
        header_frame = self._build_header_card()
        main_layout.addWidget(header_frame)

        # 2. SLIDESHOW AUTOMATION BAR
        slideshow_bar = self._build_slideshow_bar()
        main_layout.addWidget(slideshow_bar)

        # 3. MAIN BODY (Splitter: Left = Playlist/Explorer, Right = Live Preview & Transport)
        self.body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.body_splitter.setHandleWidth(5)

        left_panel = self._build_playlist_panel()
        right_panel = self._build_preview_panel()

        self.body_splitter.addWidget(left_panel)
        self.body_splitter.addWidget(right_panel)
        self.body_splitter.setStretchFactor(0, 38)
        self.body_splitter.setStretchFactor(1, 62)
        main_layout.addWidget(self.body_splitter, 1)

        # 4. BOTTOM MASTER CONTROL DECK
        bottom_deck = self._build_bottom_deck()
        main_layout.addWidget(bottom_deck)

    def _build_header_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("HeaderCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        # App branding
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(1)
        title_lbl = QLabel("DualScreen Presenter")
        title_lbl.setObjectName("AppTitle")
        sub_lbl = QLabel("Broadcast Console")
        sub_lbl.setObjectName("AppSubtitle")
        brand_layout.addWidget(title_lbl)
        brand_layout.addWidget(sub_lbl)
        layout.addLayout(brand_layout)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setObjectName("PanelSeparator")
        layout.addWidget(sep1)

        # Folder selection area
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(6)
        self.browse_btn = QPushButton("Choose Folder...")
        self.browse_btn.setToolTip("Select a folder containing images and videos")
        self.browse_btn.clicked.connect(self.on_browse_folder)
        folder_layout.addWidget(self.browse_btn)

        self.folder_path_lbl = QLabel("No folder selected")
        self.folder_path_lbl.setProperty("tone", "secondary")
        self.folder_path_lbl.setStyleSheet("font-size: 11px; font-style: italic;")
        self.folder_path_lbl.setMinimumWidth(180)
        self.folder_path_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        folder_layout.addWidget(self.folder_path_lbl, 1)

        self.recursive_chk = QCheckBox("Subfolders")
        self.recursive_chk.setToolTip("Include photos & videos in subfolders")
        self.recursive_chk.toggled.connect(self.on_recursive_toggled)
        folder_layout.addWidget(self.recursive_chk)

        self.reload_btn = QPushButton("Reload")
        self.reload_btn.setToolTip("Reload folder files")
        self.reload_btn.clicked.connect(self.on_reload_folder)
        folder_layout.addWidget(self.reload_btn)

        layout.addLayout(folder_layout, 1)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setObjectName("PanelSeparator")
        layout.addWidget(sep2)

        # Theme Switcher
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(5)
        theme_lbl = QLabel("Theme:")
        theme_lbl.setProperty("tone", "secondary")
        theme_lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
        theme_layout.addWidget(theme_lbl)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(AVAILABLE_THEMES)
        self.theme_combo.setToolTip("Select visual application theme")
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setObjectName("PanelSeparator")
        layout.addWidget(sep3)

        # Target Display Selector
        mon_layout = QHBoxLayout()
        mon_layout.setSpacing(5)
        mon_lbl = QLabel("Display:")
        mon_lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
        mon_layout.addWidget(mon_lbl)

        self.monitor_combo = QComboBox()
        self.monitor_combo.setMinimumWidth(200)
        self.monitor_combo.setToolTip("Select the monitor for fullscreen presentation")
        self.monitor_combo.currentIndexChanged.connect(self.on_screen_selection_changed)
        mon_layout.addWidget(self.monitor_combo)

        self.refresh_screens_btn = QPushButton("Refresh")
        self.refresh_screens_btn.setToolTip("Re-scan connected monitors")
        self.refresh_screens_btn.clicked.connect(self.refresh_screens)
        mon_layout.addWidget(self.refresh_screens_btn)

        layout.addLayout(mon_layout)
        return card

    def _build_slideshow_bar(self) -> QFrame:
        """Bar for automated timed slideshow controls and countdown progress."""
        bar = QFrame()
        bar.setObjectName("SlideshowBanner")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Slideshow Play / Pause Button
        self.slideshow_toggle_btn = QPushButton("Start Slideshow")
        self.slideshow_toggle_btn.setObjectName("SlideshowToggleBtn")
        self.slideshow_toggle_btn.setToolTip("Start or pause automated timed slideshow (P)")
        self.slideshow_toggle_btn.clicked.connect(self.toggle_slideshow)
        layout.addWidget(self.slideshow_toggle_btn)

        # Interval Selector
        int_lbl = QLabel("Interval:")
        int_lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
        layout.addWidget(int_lbl)

        self.interval_combo = QComboBox()
        self.interval_combo.addItem("2 seconds", 2)
        self.interval_combo.addItem("3 seconds", 3)
        self.interval_combo.addItem("5 seconds", 5)
        self.interval_combo.addItem("8 seconds", 8)
        self.interval_combo.addItem("10 seconds", 10)
        self.interval_combo.addItem("15 seconds", 15)
        self.interval_combo.addItem("20 seconds", 20)
        self.interval_combo.addItem("30 seconds", 30)
        self.interval_combo.addItem("60 seconds", 60)
        self.interval_combo.setCurrentIndex(2)  # Default 5s
        self.interval_combo.currentIndexChanged.connect(self.on_interval_changed)
        layout.addWidget(self.interval_combo)

        # Auto-start with Projecting Checkbox
        self.autostart_chk = QCheckBox("Auto-start with Projecting")
        self.autostart_chk.setChecked(True)
        self.autostart_chk.setToolTip("Automatically start timed slideshow when 'Start Projecting' is clicked")
        layout.addWidget(self.autostart_chk)

        # Wait for video to finish checkbox
        self.video_wait_chk = QCheckBox("Let videos finish")
        self.video_wait_chk.setChecked(True)
        self.video_wait_chk.setToolTip("During timed slideshow, allow videos to play completely before advancing")
        layout.addWidget(self.video_wait_chk)

        # Countdown Progress Bar
        self.countdown_bar = QProgressBar()
        self.countdown_bar.setRange(0, 100)
        self.countdown_bar.setValue(0)
        self.countdown_bar.setTextVisible(False)
        self.countdown_bar.setMinimumWidth(80)
        self.countdown_bar.setToolTip("Time remaining before next slide transition")
        layout.addWidget(self.countdown_bar, 1)

        # Time remaining label
        self.countdown_lbl = QLabel("Manual Advance")
        self.countdown_lbl.setProperty("tone", "secondary")
        self.countdown_lbl.setStyleSheet("font-size: 11px; font-weight: 600; min-width: 85px;")
        layout.addWidget(self.countdown_lbl)

        return bar

    def _build_playlist_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files...")
        self.search_input.textChanged.connect(self.on_search_changed)
        filter_layout.addWidget(self.search_input, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Sort: Name (A-Z)", "name_asc")
        self.sort_combo.addItem("Sort: Name (Z-A)", "name_desc")
        self.sort_combo.addItem("Sort: Date", "date_desc")
        self.sort_combo.addItem("Sort: Size", "size_desc")
        self.sort_combo.addItem("Sort: Type", "type_asc")
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        filter_layout.addWidget(self.sort_combo)

        layout.addLayout(filter_layout)

        # Type filter chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(4)

        self.chip_all = QPushButton("All")
        self.chip_all.setCheckable(True)
        self.chip_all.setChecked(True)
        self.chip_all.clicked.connect(lambda: self.set_media_filter("all"))

        self.chip_photos = QPushButton("Photos")
        self.chip_photos.setCheckable(True)
        self.chip_photos.clicked.connect(lambda: self.set_media_filter("image"))

        self.chip_videos = QPushButton("Videos")
        self.chip_videos.setCheckable(True)
        self.chip_videos.clicked.connect(lambda: self.set_media_filter("video"))

        for chip in (self.chip_all, self.chip_photos, self.chip_videos):
            chip.setProperty("mediaFilter", True)
            chips_layout.addWidget(chip)

        chips_layout.addStretch()

        self.shuffle_order_btn = QPushButton("Shuffle List")
        self.shuffle_order_btn.setToolTip("Randomize playlist sequence order")
        self.shuffle_order_btn.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        self.shuffle_order_btn.clicked.connect(self.on_shuffle_playlist_order)
        chips_layout.addWidget(self.shuffle_order_btn)

        layout.addLayout(chips_layout)

        # Playlist List
        self.playlist_widget = QListWidget()
        self.playlist_widget.setIconSize(QSize(20, 20))
        self.playlist_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.playlist_widget.currentRowChanged.connect(self.on_list_selection_changed)
        layout.addWidget(self.playlist_widget, 1)

        # Playlist Stats footer
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("0 items")
        self.stats_label.setProperty("tone", "muted")
        self.stats_label.setStyleSheet("font-size: 11px; font-weight: 500;")
        stats_layout.addWidget(self.stats_label)

        stats_layout.addStretch()

        self.loop_video_chk = QCheckBox("Loop Video (manual mode)")
        self.loop_video_chk.setChecked(True)
        self.loop_video_chk.setToolTip("Repeat video continuously when not in automated slideshow mode")
        self.loop_video_chk.setProperty("tone", "secondary")
        self.loop_video_chk.setStyleSheet("font-size: 11px;")
        stats_layout.addWidget(self.loop_video_chk)

        layout.addLayout(stats_layout)

        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Live Preview Monitor Screen
        self.preview_widget = PreviewWidget(self)
        layout.addWidget(self.preview_widget, 1)

        # Video Transport & Timeline Bar
        self.transport_frame = QFrame()
        self.transport_frame.setObjectName("TransportFrame")
        trans_layout = QHBoxLayout(self.transport_frame)
        trans_layout.setContentsMargins(6, 3, 6, 3)
        trans_layout.setSpacing(8)

        self.play_pause_btn = QPushButton("Pause")
        self.play_pause_btn.setToolTip("Play / Pause Video (Space)")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        trans_layout.addWidget(self.play_pause_btn)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setProperty("tone", "secondary")
        self.time_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        trans_layout.addWidget(self.time_label)

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setObjectName("TimelineSlider")
        self.timeline_slider.setRange(0, 1000)
        self.timeline_slider.sliderMoved.connect(self.on_timeline_slider_moved)
        self.timeline_slider.sliderPressed.connect(self.on_timeline_slider_pressed)
        self.timeline_slider.sliderReleased.connect(self.on_timeline_slider_released)
        trans_layout.addWidget(self.timeline_slider, 1)

        layout.addWidget(self.transport_frame)

        # Metadata bar below preview
        meta_frame = QFrame()
        meta_frame.setObjectName("MetadataFrame")
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(6, 3, 6, 3)

        self.meta_title_lbl = QLabel("No media active")
        self.meta_title_lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
        meta_layout.addWidget(self.meta_title_lbl, 1)

        self.meta_info_lbl = QLabel("")
        self.meta_info_lbl.setProperty("tone", "muted")
        self.meta_info_lbl.setStyleSheet("font-size: 11px;")
        meta_layout.addWidget(self.meta_info_lbl)

        layout.addWidget(meta_frame)

        return panel

    def _build_bottom_deck(self) -> QFrame:
        deck = QFrame()
        deck.setObjectName("MasterDeck")
        layout = QHBoxLayout(deck)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # SECTION A: Projecting Power (Start / Stop Projecting)
        show_power_layout = QHBoxLayout()
        show_power_layout.setSpacing(6)

        self.start_proj_btn = QPushButton("Start Projecting")
        self.start_proj_btn.setObjectName("StartProjBtn")
        self.start_proj_btn.setToolTip("Start fullscreen projection onto the selected secondary display (F5)")
        self.start_proj_btn.clicked.connect(self.start_projecting)
        show_power_layout.addWidget(self.start_proj_btn)

        self.stop_proj_btn = QPushButton("Stop Projecting")
        self.stop_proj_btn.setObjectName("StopProjBtn")
        self.stop_proj_btn.setToolTip("Stop fullscreen projection and close secondary monitor display (Esc)")
        self.stop_proj_btn.setEnabled(False)
        self.stop_proj_btn.clicked.connect(self.stop_projecting)
        show_power_layout.addWidget(self.stop_proj_btn)

        layout.addLayout(show_power_layout)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setObjectName("PanelSeparator")
        layout.addWidget(sep1)

        # SECTION B: Navigation (Back, Random Checkbox, Next)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)

        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("NavBackBtn")
        self.back_btn.setToolTip("Previous item (Left Arrow / PageUp)")
        self.back_btn.clicked.connect(self.on_nav_back)
        nav_layout.addWidget(self.back_btn)

        self.random_chk = QCheckBox("Random")
        self.random_chk.setToolTip("When checked, Next advances randomly and Back steps back in history (R)")
        self.random_chk.toggled.connect(self.on_random_chk_toggled)
        nav_layout.addWidget(self.random_chk)

        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("NavNextBtn")
        self.next_btn.setToolTip("Next item (Right Arrow / Space / PageDown)")
        self.next_btn.clicked.connect(self.on_nav_next)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setObjectName("PanelSeparator")
        layout.addWidget(sep2)

        # SECTION C: Volume & Audio Control Deck — Vol label | slider | % | [Mute]
        layout.addStretch(1)  # Push volume section to the far right

        vol_layout = QHBoxLayout()
        vol_layout.setSpacing(6)

        vol_lbl = QLabel("Vol:")
        vol_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        vol_layout.addWidget(vol_lbl)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(self._last_volume)
        self.vol_slider.setFixedWidth(110)
        self.vol_slider.setToolTip("Master Volume (Up / Down arrows)")
        self.vol_slider.valueChanged.connect(self.on_volume_changed)
        vol_layout.addWidget(self.vol_slider)

        self.vol_label = QLabel(f"{self._last_volume}%")
        self.vol_label.setFixedWidth(30)
        self.vol_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        vol_layout.addWidget(self.vol_label)

        # Compact mute button — lives to the right of the volume readout
        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setObjectName("MuteBtn")
        self.mute_btn.setToolTip("Toggle Mute (M)")
        self.mute_btn.setMinimumWidth(76)
        self.mute_btn.clicked.connect(self.toggle_mute)
        vol_layout.addWidget(self.mute_btn)

        layout.addLayout(vol_layout)

        return deck

    def _init_shortcuts(self):
        """
        Keyboard shortcuts — navigation keys use ApplicationShortcut so they fire
        even when the projector window (secondary monitor) has focus, making the app
        fully compatible with standard wireless presenter remotes (Logitech, Kensington,
        etc.) that emit Page Down / Page Up / F5 / Escape / Period key codes.
        """
        def _sc(key, slot, app_wide=False):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            if app_wide:
                sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            return sc

        # --- Navigation (presenter remote compatible) ---
        # Most remotes: Next = Page Down / Right,  Prev = Page Up / Left
        _sc(Qt.Key.Key_Right,    self.on_nav_next, app_wide=True)
        _sc(Qt.Key.Key_PageDown, self.on_nav_next, app_wide=True)
        _sc(Qt.Key.Key_Left,     self.on_nav_back, app_wide=True)
        _sc(Qt.Key.Key_PageUp,   self.on_nav_back, app_wide=True)

        # Space — WindowShortcut to avoid colliding with text-field input
        _sc(Qt.Key.Key_Space, self.on_nav_next)

        # --- Projecting start / stop (F5 = standard remote "Start Show" key) ---
        _sc(Qt.Key.Key_F5,     self.start_projecting, app_wide=True)
        _sc(Qt.Key.Key_Escape, self.stop_projecting,  app_wide=True)

        # --- Blank / unblank projector ---
        # "B" and "." (period) are the de-facto blank-screen keys on presenter remotes
        _sc(Qt.Key.Key_B,      self.toggle_projector_blank, app_wide=True)
        _sc(Qt.Key.Key_Period, self.toggle_projector_blank, app_wide=True)

        # --- Slideshow / random / mute --- (WindowShortcut — avoid conflicts)
        _sc(Qt.Key.Key_P, self.toggle_slideshow)
        _sc(Qt.Key.Key_R, self.toggle_random_chk)
        _sc(Qt.Key.Key_M, self.toggle_mute)

        # --- Volume ---
        _sc(Qt.Key.Key_Up,   self.volume_up)
        _sc(Qt.Key.Key_Down, self.volume_down)

    def _connect_player_signals(self):
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.durationChanged.connect(self.on_player_duration_changed)
        self.player.playbackStateChanged.connect(self.on_player_state_changed)
        self.player.mediaStatusChanged.connect(self.on_player_media_status_changed)

    # ==================== THEME MANAGEMENT ====================

    def on_theme_changed(self, theme_name: str):
        self.current_theme = theme_name
        qss = get_theme_qss(theme_name)
        QApplication.instance().setStyleSheet(qss)
        self.preview_widget.set_theme(theme_name)
        self._update_media_icons()

    def _update_media_icons(self):
        palette = THEME_PALETTES.get(self.current_theme, THEME_PALETTES["Obsidian Neon"])
        self._media_type_icons = {
            "image": _media_type_icon(False, QColor(palette["accent_glow"])),
            "video": _media_type_icon(True, QColor(palette["accent_slideshow"]).lighter(140)),
        }
        for index, item in enumerate(self.media_mgr.filtered_items):
            row = self.playlist_widget.item(index)
            if row is not None:
                row.setIcon(self._media_type_icons[item.media_type])

    # ==================== DISPLAY DETECTION & MANAGEMENT ====================

    def refresh_screens(self):
        """Scan system displays and populate target display selector."""
        screens = QGuiApplication.screens()
        primary_screen = QGuiApplication.primaryScreen()
        self.monitor_combo.clear()

        secondary_index = 0
        for i, s in enumerate(screens):
            is_primary = (s == primary_screen)
            geo = s.geometry()
            name = s.name()
            tag = "Primary" if is_primary else "Secondary"
            label = f"[{tag}] Monitor {i + 1}: {name} ({geo.width()}x{geo.height()})"
            self.monitor_combo.addItem(label, userData=i)
            if not is_primary:
                secondary_index = i

        # Default to secondary monitor if dual-screen is detected
        if len(screens) > 1:
            self.monitor_combo.setCurrentIndex(secondary_index)
        elif self.monitor_combo.count() > 0:
            self.monitor_combo.setCurrentIndex(0)

        self._update_preview_monitor_status()

    def get_selected_screen(self) -> Optional[QScreen]:
        screens = QGuiApplication.screens()
        idx = self.monitor_combo.currentData()
        if idx is not None and 0 <= idx < len(screens):
            return screens[idx]
        return QGuiApplication.primaryScreen()

    def on_screen_selection_changed(self):
        self._update_preview_monitor_status()
        if self.is_projecting and self.projector_window:
            target_screen = self.get_selected_screen()
            if target_screen:
                self.projector_window.show_on_screen(target_screen)

    def _update_preview_monitor_status(self):
        screen = self.get_selected_screen()
        name = screen.name() if screen else "Monitor"
        res = f"{screen.geometry().width()}x{screen.geometry().height()}" if screen else ""
        self.preview_widget.set_projector_status(self.is_projecting, name, res)

    # ==================== PROJECTING START / STOP ====================

    def start_projecting(self):
        """Launch the fullscreen projection window on the selected monitor."""
        target_screen = self.get_selected_screen()
        if not target_screen:
            QMessageBox.warning(self, "No Display", "No monitor detected.")
            return

        if not self.projector_window:
            self.projector_window = ProjectorWindow()
            self.projector_window.close_requested.connect(self.stop_projecting)
            self.projector_window.next_requested.connect(self.on_nav_next)
            self.projector_window.prev_requested.connect(self.on_nav_back)

        self.is_projecting = True
        self.start_proj_btn.setEnabled(False)
        self.stop_proj_btn.setEnabled(True)

        # Show fullscreen on the chosen secondary monitor
        self.projector_window.show_on_screen(target_screen)
        self._update_preview_monitor_status()

        # Display current media item on projector
        current_item = self.media_mgr.get_current_item()
        if current_item:
            self.display_item(current_item)

        # If user checked 'Auto-start with Projecting', start the timed slideshow
        if self.autostart_chk.isChecked() and not self.slideshow_running:
            self.start_slideshow()

    def stop_projecting(self):
        """Close fullscreen projection on the secondary monitor."""
        if not self.is_projecting:
            return

        self.is_projecting = False
        self.start_proj_btn.setEnabled(True)
        self.stop_proj_btn.setEnabled(False)

        if self.projector_window:
            self.projector_window.show_blank()
            self.projector_window.close()

        self._update_preview_monitor_status()

    def toggle_projector_blank(self):
        """
        Toggle blank (black) screen on the projector.
        Mapped to 'B' and '.' — the standard blank-screen keys on presenter remotes
        (Logitech R400/R800, Kensington, etc.).
        When blanked, pressing again restores the current media item.
        """
        if not self.is_projecting or not self.projector_window:
            return
        if self.projector_window.mode == 'blank':
            # Restore current media
            current = self.media_mgr.get_current_item()
            if current:
                self.display_item(current)
        else:
            self.projector_window.show_blank()
            self._update_preview_monitor_status()

    # ==================== TIMED SLIDESHOW AUTOMATION ====================

    def toggle_slideshow(self):
        if self.slideshow_running:
            self.pause_slideshow()
        else:
            self.start_slideshow()

    def start_slideshow(self):
        if not self.media_mgr.filtered_items:
            return

        self.slideshow_running = True
        self.slideshow_toggle_btn.setText("Pause Slideshow")
        self.slideshow_toggle_btn.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 #d97706);
            color: #ffffff; border: 1px solid #f59e0b; border-radius: 5px; padding: 4px 10px;
            font-size: 11px; font-weight: 700;
        """)

        self._reset_slideshow_timer()
        self.slideshow_timer.start()
        self._update_slideshow_ui_status()

    def pause_slideshow(self):
        self.slideshow_running = False
        self.slideshow_toggle_btn.setText("Start Slideshow")
        self.slideshow_toggle_btn.setStyleSheet("")
        self.slideshow_timer.stop()
        self.countdown_bar.setValue(0)
        self.countdown_lbl.setText("Slideshow Paused")
        self._update_slideshow_ui_status()

    def on_interval_changed(self):
        sec = self.interval_combo.currentData()
        if sec:
            self.slideshow_interval_ms = sec * 1000
            self._reset_slideshow_timer()
            self._update_slideshow_ui_status()

    def on_random_chk_toggled(self, checked: bool):
        self._update_slideshow_ui_status()

    def toggle_random_chk(self):
        self.random_chk.setChecked(not self.random_chk.isChecked())

    def _reset_slideshow_timer(self):
        self._slideshow_remaining_ms = self.slideshow_interval_ms
        self.countdown_bar.setValue(100)

    def _on_slideshow_tick(self):
        if not self.slideshow_running:
            return

        current_item = self.media_mgr.get_current_item()
        # If currently playing video and 'Let videos finish' is checked:
        if current_item and current_item.is_video and self.video_wait_chk.isChecked():
            dur = self.player.duration()
            pos = self.player.position()
            if dur > 0:
                pct = int((pos / dur) * 100)
                self.countdown_bar.setValue(pct)
                rem_sec = max(0, (dur - pos) // 1000)
                self.countdown_lbl.setText(f"Video: {rem_sec}s left")
            return

        # Otherwise standard interval countdown
        self._slideshow_remaining_ms -= 100
        if self._slideshow_remaining_ms <= 0:
            self.on_nav_next()
            self._reset_slideshow_timer()
        else:
            pct = int((self._slideshow_remaining_ms / max(1, self.slideshow_interval_ms)) * 100)
            self.countdown_bar.setValue(pct)
            sec_left = (self._slideshow_remaining_ms + 900) // 1000
            self.countdown_lbl.setText(f"Next in {sec_left}s")

    def _update_slideshow_ui_status(self):
        sec = self.slideshow_interval_ms // 1000
        mode = "Random" if self.random_chk.isChecked() else "Sequential"
        if self.slideshow_running:
            info = f"SLIDESHOW ACTIVE • {sec}s ({mode})"
        else:
            info = ""
        self.preview_widget.set_slideshow_status(self.slideshow_running, info)

    # ==================== FOLDER & MEDIA LOADING ====================

    def on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder of Images and Videos",
            self.media_mgr.current_folder or os.path.expanduser("~")
        )
        if folder:
            self.load_folder(folder)

    def on_reload_folder(self):
        if self.media_mgr.current_folder:
            self.load_folder(self.media_mgr.current_folder)

    def on_recursive_toggled(self, checked: bool):
        if self.media_mgr.current_folder:
            self.load_folder(self.media_mgr.current_folder)

    def load_folder(self, folder_path: str):
        recursive = self.recursive_chk.isChecked()
        count = self.media_mgr.load_folder(folder_path, recursive=recursive)
        self.folder_path_lbl.setText(folder_path)
        self.folder_path_lbl.setToolTip(folder_path)
        self.refresh_playlist_ui()

        # Display first item if available
        if count > 0:
            first = self.media_mgr.jump_to_index(0)
            if first:
                self.display_item(first)
        else:
            self.preview_widget.clear()
            self.meta_title_lbl.setText("No images or videos found in folder")
            self.meta_info_lbl.setText("")

    def refresh_playlist_ui(self):
        """Repopulate the QListWidget from filtered media items."""
        self.playlist_widget.blockSignals(True)
        self.playlist_widget.clear()
        if not self._media_type_icons:
            self._update_media_icons()

        for item in self.media_mgr.filtered_items:
            list_item = QListWidgetItem(
                self._media_type_icons[item.media_type],
                f"{item.filename}  ({item.size_str})",
            )
            list_item.setToolTip(f"{item.path}\nType: {item.media_type.upper()}\nSize: {item.size_str}")
            self.playlist_widget.addItem(list_item)

        cur_idx = self.media_mgr.current_index
        if 0 <= cur_idx < self.playlist_widget.count():
            self.playlist_widget.setCurrentRow(cur_idx)

        self.playlist_widget.blockSignals(False)

        # Update stats
        n_img = self.media_mgr.image_count()
        n_vid = self.media_mgr.video_count()
        total = self.media_mgr.count()
        self.stats_label.setText(f"{total} items ({n_img} photos, {n_vid} videos)")

    def on_list_selection_changed(self, row: int):
        if row >= 0 and row != self.media_mgr.current_index:
            item = self.media_mgr.jump_to_index(row)
            if item:
                self.display_item(item)
                if self.slideshow_running:
                    self._reset_slideshow_timer()

    def on_item_double_clicked(self, list_item: QListWidgetItem):
        row = self.playlist_widget.row(list_item)
        if row >= 0:
            item = self.media_mgr.jump_to_index(row)
            if item:
                self.display_item(item)
                if self.slideshow_running:
                    self._reset_slideshow_timer()

    def on_search_changed(self, text: str):
        self.media_mgr.search_query = text
        self.media_mgr.apply_filter_and_sort()
        self.refresh_playlist_ui()
        curr = self.media_mgr.get_current_item()
        if curr:
            self.display_item(curr)

    def set_media_filter(self, filter_type: str):
        self.chip_all.setChecked(filter_type == "all")
        self.chip_photos.setChecked(filter_type == "image")
        self.chip_videos.setChecked(filter_type == "video")
        self.media_mgr.media_filter = filter_type
        self.media_mgr.apply_filter_and_sort()
        self.refresh_playlist_ui()
        curr = self.media_mgr.get_current_item()
        if curr:
            self.display_item(curr)

    def on_sort_changed(self):
        data = self.sort_combo.currentData()
        if data == "name_asc":
            self.media_mgr.sort_key, self.media_mgr.sort_ascending = "name", True
        elif data == "name_desc":
            self.media_mgr.sort_key, self.media_mgr.sort_ascending = "name", False
        elif data == "date_desc":
            self.media_mgr.sort_key, self.media_mgr.sort_ascending = "date", False
        elif data == "size_desc":
            self.media_mgr.sort_key, self.media_mgr.sort_ascending = "size", False
        elif data == "type_asc":
            self.media_mgr.sort_key, self.media_mgr.sort_ascending = "type", True
        self.media_mgr.apply_filter_and_sort()
        self.refresh_playlist_ui()

    def on_shuffle_playlist_order(self):
        import random
        random.shuffle(self.media_mgr.filtered_items)
        self.media_mgr.current_index = 0 if self.media_mgr.filtered_items else -1
        self.refresh_playlist_ui()
        curr = self.media_mgr.get_current_item()
        if curr:
            self.display_item(curr)

    # ==================== NAVIGATION (MANUAL & AUTOMATED) ====================

    def on_nav_next(self):
        """
        When 'Random' checkbox is checked, Next picks a random item.
        Otherwise advances sequentially.
        """
        if self.random_chk.isChecked():
            item = self.media_mgr.random_item()
        else:
            item = self.media_mgr.next_item()

        if item:
            self._sync_playlist_selection()
            self.display_item(item)
            if self.slideshow_running:
                self._reset_slideshow_timer()

    def on_nav_back(self):
        """
        When 'Random' checkbox is checked, Back steps back in random history.
        Otherwise moves backward sequentially.
        """
        item = self.media_mgr.prev_item()
        if item:
            self._sync_playlist_selection()
            self.display_item(item)
            if self.slideshow_running:
                self._reset_slideshow_timer()

    def _sync_playlist_selection(self):
        idx = self.media_mgr.current_index
        self.playlist_widget.blockSignals(True)
        self.playlist_widget.setCurrentRow(idx)
        list_item = self.playlist_widget.item(idx)
        if list_item:
            self.playlist_widget.scrollToItem(list_item)
        self.playlist_widget.blockSignals(False)

    # ==================== DISPLAY & PLAYBACK DISPATCH ====================

    def display_item(self, item: MediaItem):
        """Present media item on both preview monitor and secondary projector."""
        idx_str = f"[{self.media_mgr.current_index + 1} of {self.media_mgr.count()}]"
        self.meta_title_lbl.setText(f"{idx_str}  {item.filename}")
        self.meta_info_lbl.setText(f"{item.media_type.upper()} • {item.size_str}")

        if item.is_image:
            self.transport_frame.hide()
            self.player.stop()

            # 1. Update Preview
            self.preview_widget.set_image(item)

            # 2. Update Projector
            if self.is_projecting and self.projector_window:
                self.projector_window.display_image(item)

        elif item.is_video:
            self.transport_frame.show()
            self.play_pause_btn.setText("Pause")
            self.preview_widget.set_video(item)

            if self.is_projecting and self.projector_window:
                self.projector_window.prepare_for_video(item)

            self.player.setSource(QUrl.fromLocalFile(item.path))
            self.player.play()

    def _on_video_frame(self, frame):
        """Unified video frame receiver: mirrors to preview and projector screen."""
        self.preview_widget.update_video_frame(frame)
        if self.is_projecting and self.projector_window:
            self.projector_window.update_video_frame(frame)

    # ==================== VIDEO PLAYBACK CONTROLS ====================

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def on_player_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("Pause")
        else:
            self.play_pause_btn.setText("Play")

    def on_player_position_changed(self, position_ms: int):
        if not self._is_scrubbing:
            duration = self.player.duration()
            if duration > 0:
                val = int((position_ms / duration) * 1000)
                self.timeline_slider.setValue(val)
            self._update_time_label(position_ms, duration)

    def on_player_duration_changed(self, duration_ms: int):
        self._update_time_label(self.player.position(), duration_ms)

    def _update_time_label(self, cur_ms: int, tot_ms: int):
        cur_s = cur_ms // 1000
        tot_s = tot_ms // 1000
        self.time_label.setText(f"{cur_s // 60:02d}:{cur_s % 60:02d} / {tot_s // 60:02d}:{tot_s % 60:02d}")

    def on_timeline_slider_pressed(self):
        self._is_scrubbing = True

    def on_timeline_slider_moved(self, value: int):
        duration = self.player.duration()
        if duration > 0:
            target_pos = int((value / 1000.0) * duration)
            self._update_time_label(target_pos, duration)

    def on_timeline_slider_released(self):
        self._is_scrubbing = False
        duration = self.player.duration()
        if duration > 0:
            target_pos = int((self.timeline_slider.value() / 1000.0) * duration)
            self.player.setPosition(target_pos)

    def on_player_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.slideshow_running and self.video_wait_chk.isChecked():
                self.on_nav_next()
                self._reset_slideshow_timer()
            elif self.loop_video_chk.isChecked():
                self.player.setPosition(0)
                self.player.play()
            else:
                self.player.pause()

    # ==================== VOLUME CONTROLS ====================

    def on_volume_changed(self, value: int):
        self._last_volume = value
        self.audio_output.setVolume(value / 100.0)
        self.vol_label.setText(f"{value}%")
        if self.audio_output.isMuted() and value > 0:
            self.audio_output.setMuted(False)
            self.mute_btn.setText("Mute")

    def toggle_mute(self):
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        if muted:
            self.mute_btn.setText("Unmute")
            self.vol_label.setText("Mute")
        else:
            self.mute_btn.setText("Mute")
            self.vol_label.setText(f"{self.vol_slider.value()}%")

    def volume_up(self):
        val = min(100, self.vol_slider.value() + 5)
        self.vol_slider.setValue(val)

    def volume_down(self):
        val = max(0, self.vol_slider.value() - 5)
        self.vol_slider.setValue(val)

    # ==================== DRAG & DROP ====================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        first_path = urls[0].toLocalFile()
        if os.path.isdir(first_path):
            self.load_folder(first_path)
            event.acceptProposedAction()
        elif os.path.isfile(first_path):
            parent_dir = os.path.dirname(first_path)
            self.load_folder(parent_dir)
            fname = os.path.basename(first_path)
            for i, it in enumerate(self.media_mgr.filtered_items):
                if it.filename == fname:
                    self.media_mgr.jump_to_index(i)
                    self._sync_playlist_selection()
                    self.display_item(it)
                    break
            event.acceptProposedAction()

    # ==================== SETTINGS PERSISTENCE ====================

    def _load_settings(self):
        """
        Restore all user-configurable settings saved in the previous session.
        On the very first launch (no saved settings) the sample_media folder is
        loaded as the default, and all control defaults remain as designed.
        """
        s = QSettings("Antigravity", "DualScreenPresenter")

        # --- Window geometry & splitter ---
        geom = s.value("window/geometry")
        if geom:
            self.restoreGeometry(geom)
        splitter_state = s.value("window/splitter_state")
        if splitter_state:
            self.body_splitter.restoreState(splitter_state)

        # --- Theme ---
        theme = s.value("ui/theme", "Obsidian Neon")
        if theme in AVAILABLE_THEMES:
            # Block the signal temporarily to avoid double-apply on startup
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(theme)
            self.theme_combo.blockSignals(False)
            self.on_theme_changed(theme)

        # --- Target monitor: match by display-name string, fall back to index ---
        saved_mon_label = s.value("display/monitor_label", "")
        if saved_mon_label:
            for i in range(self.monitor_combo.count()):
                if saved_mon_label in self.monitor_combo.itemText(i):
                    self.monitor_combo.setCurrentIndex(i)
                    break
        else:
            saved_idx = s.value("display/monitor_index")
            if saved_idx is not None:
                idx = int(saved_idx)
                if 0 <= idx < self.monitor_combo.count():
                    self.monitor_combo.setCurrentIndex(idx)

        # --- Slideshow ---
        interval_idx = s.value("slideshow/interval_index", 2)
        try:
            self.interval_combo.setCurrentIndex(int(interval_idx))
            self.on_interval_changed()          # sync internal ms counter
        except Exception:
            pass
        self.autostart_chk.setChecked(_to_bool(s.value("slideshow/autostart", True)))
        self.video_wait_chk.setChecked(_to_bool(s.value("slideshow/video_wait", True)))

        # --- Navigation ---
        self.random_chk.setChecked(_to_bool(s.value("nav/random", False)))

        # --- Playback ---
        self.loop_video_chk.setChecked(_to_bool(s.value("playback/loop_video", True)))

        # --- Audio ---
        volume = s.value("audio/volume", 75)
        try:
            self.vol_slider.setValue(int(volume))
        except Exception:
            pass
        if _to_bool(s.value("audio/muted", False)):
            self.toggle_mute()

        # --- Folder options ---
        self.recursive_chk.setChecked(_to_bool(s.value("folder/recursive", False)))
        sort_key = s.value("folder/sort_key", "name_asc")
        sort_idx = self.sort_combo.findData(sort_key)
        if sort_idx >= 0:
            self.sort_combo.blockSignals(True)
            self.sort_combo.setCurrentIndex(sort_idx)
            self.sort_combo.blockSignals(False)
            self.on_sort_changed()              # apply sort without double reload

        # --- Last opened folder (or sample_media on first run) ---
        last_folder = s.value("folder/last_path", "")
        if last_folder and os.path.isdir(last_folder):
            self.load_folder(last_folder)
        else:
            # First launch: load bundled sample_media if present
            # In a one-file build, __file__ points inside the extracted bundle.
            app_dir = os.path.dirname(os.path.abspath(__file__))
            sample_dir = os.path.join(app_dir, "sample_media")
            if not os.path.isdir(sample_dir) and getattr(sys, 'frozen', False):
                sample_dir = os.path.join(os.path.dirname(sys.executable), "sample_media")
            if os.path.isdir(sample_dir):
                self.load_folder(sample_dir)

    def _save_settings(self):
        """Persist every user-configurable setting to disk."""
        s = QSettings("Antigravity", "DualScreenPresenter")

        # Window
        s.setValue("window/geometry",      self.saveGeometry())
        s.setValue("window/splitter_state", self.body_splitter.saveState())

        # Theme
        s.setValue("ui/theme", self.current_theme)

        # Monitor — store both the full label and the index for robust matching
        s.setValue("display/monitor_index", self.monitor_combo.currentIndex())
        s.setValue("display/monitor_label", self.monitor_combo.currentText())

        # Slideshow
        s.setValue("slideshow/interval_index", self.interval_combo.currentIndex())
        s.setValue("slideshow/autostart",      self.autostart_chk.isChecked())
        s.setValue("slideshow/video_wait",     self.video_wait_chk.isChecked())

        # Navigation
        s.setValue("nav/random", self.random_chk.isChecked())

        # Playback
        s.setValue("playback/loop_video", self.loop_video_chk.isChecked())

        # Audio
        s.setValue("audio/volume", self.vol_slider.value())
        s.setValue("audio/muted",  self.audio_output.isMuted())

        # Folder
        s.setValue("folder/recursive", self.recursive_chk.isChecked())
        s.setValue("folder/sort_key",  self.sort_combo.currentData())
        if self.media_mgr.current_folder:
            s.setValue("folder/last_path", self.media_mgr.current_folder)

        s.sync()   # flush to disk immediately

    def closeEvent(self, event):
        """Clean teardown on app close — persist settings before exit."""
        self._save_settings()
        self.slideshow_timer.stop()
        self.player.stop()
        if self.projector_window:
            self.projector_window.close()
        event.accept()

