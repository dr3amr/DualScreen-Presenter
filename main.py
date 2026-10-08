"""
main.py - Entry point for DualScreen Presenter — Broadcast Console.
Initializes DPI scaling, QApplication, dark theme styles, and launches the presenter app.
"""

import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor

from presenter_app import PresenterApp
from styles import get_theme_qss


def create_app_icon() -> QIcon:
    """Generate a high-res programmatic icon for the application taskbar and window."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Monitor 1 (Main Control)
    painter.setBrush(QColor("#1e293b"))
    painter.setPen(QColor("#38bdf8"))
    painter.drawRoundedRect(4, 10, 32, 24, 4, 4)

    # Monitor 2 (Projector Display)
    painter.setBrush(QColor("#0f172a"))
    painter.setPen(QColor("#10b981"))
    painter.drawRoundedRect(28, 22, 32, 24, 4, 4)

    # Play symbol inside projector
    painter.setBrush(QColor("#10b981"))
    painter.setPen(Qt.PenStyle.NoPen)
    from PyQt6.QtGui import QPolygonF
    from PyQt6.QtCore import QPointF
    triangle = QPolygonF([QPointF(40, 29), QPointF(40, 39), QPointF(49, 34)])
    painter.drawPolygon(triangle)

    painter.end()
    return QIcon(pix)


def main():
    # Tell Windows to treat this app with its own taskbar grouping
    try:
        app_id = "antigravity.dualscreenpresenter.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

    # High DPI scaling configuration
    if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, 'PassThrough'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("DualScreen Presenter")
    app.setApplicationDisplayName("DualScreen Presenter — Broadcast Console")
    app.setOrganizationName("Antigravity")
    app.setStyleSheet(get_theme_qss("Obsidian Neon"))

    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    if os.path.isfile(ico_path):
        app_icon = QIcon(ico_path)
    else:
        app_icon = create_app_icon()
    app.setWindowIcon(app_icon)

    window = PresenterApp()
    window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
