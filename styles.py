"""
styles.py - Multi-theme design system for DualScreen Presenter — Broadcast Console.
Provides broadcast-grade dark themes with polished micro-interactions,
compact themed buttons, glassmorphism-inspired cards, and custom sliders.
"""

from pathlib import Path

CHECKBOX_CHECK_IMAGE = (Path(__file__).resolve().parent / "assets" / "checkbox-check.svg").as_posix()
DROPDOWN_ARROW_IMAGE = (Path(__file__).resolve().parent / "assets" / "dropdown-arrow.svg").as_posix()

AVAILABLE_THEMES = [
    "Obsidian Neon",
    "Midnight Studio",
    "Cyberpunk Amber",
    "Slate Graphite",
    "Dark Gray",
]

THEME_PALETTES = {
    "Obsidian Neon": {
        "bg_main": "#06090e",
        "bg_panel": "#0c121e",
        "bg_card": "#101827",
        "bg_deck": "#090f1a",
        "bg_item": "#141e30",
        "border": "#1e293b",
        "border_focus": "#38bdf8",
        "accent_primary": "#0284c7",
        "accent_glow": "#38bdf8",
        "accent_start": "#059669",
        "accent_stop": "#dc2626",
        "accent_random": "#7c3aed",
        "accent_slideshow": "#d97706",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "highlight_row": "#1e3a8a",
    },
    "Midnight Studio": {
        "bg_main": "#080d1a",
        "bg_panel": "#0f172a",
        "bg_card": "#141e36",
        "bg_deck": "#0b1224",
        "bg_item": "#182442",
        "border": "#223152",
        "border_focus": "#60a5fa",
        "accent_primary": "#2563eb",
        "accent_glow": "#60a5fa",
        "accent_start": "#10b981",
        "accent_stop": "#ef4444",
        "accent_random": "#8b5cf6",
        "accent_slideshow": "#f59e0b",
        "text_primary": "#f1f5f9",
        "text_secondary": "#a5b4fc",
        "text_muted": "#64748b",
        "highlight_row": "#2563eb",
    },
    "Cyberpunk Amber": {
        "bg_main": "#09090b",
        "bg_panel": "#121215",
        "bg_card": "#18181c",
        "bg_deck": "#0e0e11",
        "bg_item": "#202026",
        "border": "#2e2e38",
        "border_focus": "#fbbf24",
        "accent_primary": "#d97706",
        "accent_glow": "#fbbf24",
        "accent_start": "#10b981",
        "accent_stop": "#f43f5e",
        "accent_random": "#ec4899",
        "accent_slideshow": "#f59e0b",
        "text_primary": "#fafafa",
        "text_secondary": "#cbd5e1",
        "text_muted": "#71717a",
        "highlight_row": "#78350f",
    },
    "Dark Gray": {
        "bg_main": "#1a1a1a",
        "bg_panel": "#242424",
        "bg_card": "#2c2c2c",
        "bg_deck": "#202020",
        "bg_item": "#343434",
        "border": "#484848",
        "border_focus": "#a0a0a0",
        "accent_primary": "#606060",
        "accent_glow": "#b0b0b0",
        "accent_start": "#059669",
        "accent_stop": "#dc2626",
        "accent_random": "#888888",
        "accent_slideshow": "#d97706",
        "text_primary": "#f0f0f0",
        "text_secondary": "#b8b8b8",
        "text_muted": "#909090",
        "highlight_row": "#484848",
        "nav_hover": "#505050",
        "nav_pressed": "#383838",
    },
    "Slate Graphite": {
        "bg_main": "#0f172a",
        "bg_panel": "#1e293b",
        "bg_card": "#243248",
        "bg_deck": "#131d31",
        "bg_item": "#2d3d57",
        "border": "#334155",
        "border_focus": "#14b8a6",
        "accent_primary": "#0d9488",
        "accent_glow": "#2dd4bf",
        "accent_start": "#059669",
        "accent_stop": "#e11d48",
        "accent_random": "#9333ea",
        "accent_slideshow": "#ea580c",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "highlight_row": "#134e4a",
    }
}


def get_theme_qss(theme_name: str = "Obsidian Neon") -> str:
    p = THEME_PALETTES.get(theme_name, THEME_PALETTES["Obsidian Neon"])

    return f"""
/* ==================== GLOBAL APP STYLING ==================== */
QWidget {{
    background-color: {p["bg_main"]};
    color: {p["text_primary"]};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 12px;
    selection-background-color: {p["accent_primary"]};
    selection-color: #ffffff;
}}

QMainWindow {{
    background-color: {p["bg_main"]};
}}

/* Labels and checkboxes must be transparent so parent frame background shows through */
QLabel {{
    background-color: transparent;
}}

QLabel[tone="secondary"], QCheckBox[tone="secondary"] {{
    color: {p["text_secondary"]};
}}
QLabel[tone="muted"] {{
    color: {p["text_muted"]};
}}
QFrame#PanelSeparator {{
    color: {p["border"]};
}}

QFrame#TransportFrame, QFrame#MetadataFrame {{
    background-color: {p["bg_deck"]};
    border: 1px solid {p["border"]}; border-radius: 6px; padding: 3px 6px;
}}
QFrame#MasterDeck {{
    background-color: {p["bg_deck"]};
    border: 1px solid {p["border"]}; border-radius: 8px; padding: 6px 10px;
}}
QPushButton[mediaFilter="true"] {{
    background-color: {p["bg_item"]}; color: {p["text_secondary"]};
    border: 1px solid {p["border"]}; border-radius: 4px;
    padding: 3px 8px; font-size: 11px; font-weight: 600;
}}
QPushButton[mediaFilter="true"]:checked {{
    background-color: {p["accent_primary"]}; color: #ffffff;
    border-color: {p["accent_glow"]};
}}

QToolTip {{
    background-color: {p["bg_card"]};
    color: #f8fafc;
    border: 1px solid {p["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}}

/* ==================== TOP HEADER & CARDS ==================== */
QFrame#HeaderCard {{
    background-color: {p["bg_panel"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 4px 10px;
}}

QFrame#SlideshowBanner {{
    background-color: {p["bg_panel"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 4px 10px;
}}

QLabel#AppTitle {{
    font-size: 14px;
    font-weight: 800;
    color: {p["accent_glow"]};
    letter-spacing: 0.6px;
}}

QLabel#AppSubtitle {{
    font-size: 9px;
    font-weight: 700;
    color: {p["text_muted"]};
    letter-spacing: 0.8px;
}}

/* ==================== PANELS & SPLITTERS ==================== */
QSplitter::handle {{
    background-color: {p["border"]};
    border-radius: 2px;
}}

/* ==================== COMPACT BUTTONS ==================== */
QPushButton {{
    background-color: {p["bg_item"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border"]};
    border-radius: 5px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 11px;
    outline: none;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {p["border"]};
    border-color: {p["border_focus"]};
}}

QPushButton:pressed {{
    background-color: {p["bg_deck"]};
}}

QPushButton:disabled {{
    background-color: {p["bg_main"]};
    color: {p["text_muted"]};
    border-color: {p["border"]};
}}

/* Projecting Start Button (Emerald Gradient) */
QPushButton#StartProjBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_start"]}, stop:1 #10b981);
    color: #ffffff;
    border: 1px solid #34d399;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#StartProjBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 {p["accent_start"]});
    border-color: #6ee7b7;
}}

QPushButton#StartProjBtn:pressed {{
    background-color: #064e3b;
}}

/* Projecting Stop Button (Crimson Gradient) */
QPushButton#StopProjBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_stop"]}, stop:1 #f43f5e);
    color: #ffffff;
    border: 1px solid #f87171;
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#StopProjBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #991b1b, stop:1 {p["accent_stop"]});
    border-color: #fca5a5;
}}

QPushButton#StopProjBtn:pressed {{
    background-color: #7f1d1d;
}}

/* Slideshow Play / Pause Button (Amber / Gold) */
QPushButton#SlideshowToggleBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_slideshow"]}, stop:1 #fbbf24);
    color: #ffffff;
    border: 1px solid #fcd34d;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#SlideshowToggleBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 {p["accent_slideshow"]});
    border-color: #fef08a;
}}

QPushButton#SlideshowToggleBtn:pressed {{
    background-color: #78350f;
}}

/* Nav Buttons (Next, Back) */
QPushButton#NavNextBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_primary"]}, stop:1 {p["accent_glow"]});
    color: #ffffff;
    border: 1px solid {p["accent_glow"]};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#NavNextBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p.get("nav_hover", "#1d4ed8")}, stop:1 {p["accent_primary"]});
    border-color: {p["accent_glow"]};
}}

QPushButton#NavNextBtn:pressed {{
    background-color: {p.get("nav_pressed", "#1e3a8a")};
}}

QPushButton#NavBackBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_primary"]}, stop:1 {p["accent_glow"]});
    color: #ffffff;
    border: 1px solid {p["accent_glow"]};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: 700;
}}

QPushButton#NavBackBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p.get("nav_hover", "#1d4ed8")}, stop:1 {p["accent_primary"]});
    border-color: {p["accent_glow"]};
}}

QPushButton#NavBackBtn:pressed {{
    background-color: {p.get("nav_pressed", "#1e3a8a")};
}}

/* ==================== LINE EDIT & SEARCH ==================== */
QLineEdit {{
    background-color: {p["bg_deck"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border"]};
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 11px;
}}

QLineEdit:focus {{
    border: 1px solid {p["border_focus"]};
    background-color: {p["bg_panel"]};
}}

/* ==================== COMBO BOX & SPINBOX ==================== */
QComboBox, QSpinBox {{
    background-color: {p["bg_item"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border"]};
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 600;
}}

QComboBox:hover, QSpinBox:hover {{
    border-color: {p["border_focus"]};
}}

QComboBox {{
    padding-right: 30px;
}}

QComboBox:focus, QSpinBox:focus {{
    border-color: {p["border_focus"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {p["border"]};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    background-color: {p["bg_card"]};
}}

QComboBox::drop-down:hover {{
    background-color: {p["border"]};
    border-left-color: {p["border_focus"]};
}}

QComboBox::down-arrow {{
    image: url("{DROPDOWN_ARROW_IMAGE}");
    width: 12px;
    height: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {p["bg_panel"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border"]};
    border-radius: 5px;
    selection-background-color: {p["accent_primary"]};
    selection-color: #ffffff;
    padding: 3px;
}}

/* ==================== SLIDERS ==================== */
QSlider::groove:horizontal {{
    border: none;
    height: 5px;
    background: {p["bg_card"]};
    border-radius: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {p["accent_glow"]};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {p["accent_primary"]};
    width: 12px;
    margin-top: -3px;
    margin-bottom: -3px;
    border-radius: 6px;
}}

QSlider::handle:horizontal:hover {{
    background: #ffffff;
    border-color: {p["accent_glow"]};
}}

/* Timeline scrubber */
QSlider#TimelineSlider::groove:horizontal {{
    height: 6px;
    background: {p["bg_deck"]};
    border-radius: 3px;
}}

QSlider#TimelineSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_primary"]}, stop:1 {p["accent_glow"]});
    border-radius: 3px;
}}

QSlider#TimelineSlider::handle:horizontal {{
    background: {p["accent_glow"]};
    border: 2px solid #ffffff;
    width: 12px;
    margin-top: -3px;
    margin-bottom: -3px;
    border-radius: 6px;
}}

/* ==================== PROGRESS BAR (SLIDESHOW COUNTDOWN) ==================== */
QProgressBar {{
    border: 1px solid {p["border"]};
    border-radius: 3px;
    background-color: {p["bg_deck"]};
    height: 5px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p["accent_slideshow"]}, stop:1 #fbbf24);
    border-radius: 2px;
}}

/* ==================== LIST WIDGET (PLAYLIST) ==================== */
QListWidget {{
    background-color: {p["bg_panel"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 3px;
    outline: none;
}}

QListWidget::item {{
    background-color: transparent;
    color: {p["text_primary"]};
    padding: 5px 8px;
    border-radius: 4px;
    margin-bottom: 2px;
}}

QListWidget::item:hover {{
    background-color: {p["bg_card"]};
    color: #ffffff;
}}

QListWidget::item:selected {{
    background-color: {p["highlight_row"]};
    color: #ffffff;
    border-left: 3px solid {p["accent_glow"]};
}}

/* ==================== SCROLLBARS ==================== */
QScrollBar:vertical {{
    border: none;
    background: {p["bg_panel"]};
    width: 7px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {p["border"]};
    min-height: 20px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p["border_focus"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* ==================== CHECKBOXES ==================== */
QCheckBox {{
    color: {p["text_secondary"]};
    font-size: 11px;
    font-weight: 500;
    spacing: 5px;
    background-color: transparent;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p["text_muted"]};
    border-radius: 3px;
    background-color: {p["bg_item"]};
}}

QCheckBox::indicator:hover {{
    border-color: {p["border_focus"]};
}}

QCheckBox::indicator:checked {{
    image: url("{CHECKBOX_CHECK_IMAGE}");
    background-color: {p["accent_primary"]};
    border-color: {p["accent_glow"]};
}}

QCheckBox:checked {{
    color: {p["text_primary"]};
}}

QCheckBox::indicator:focus {{
    border: 2px solid {p["border_focus"]};
}}

QCheckBox::indicator:disabled {{
    background-color: {p["bg_deck"]};
    border-color: {p["border"]};
}}

QCheckBox:disabled {{
    color: {p["text_muted"]};
}}
"""
