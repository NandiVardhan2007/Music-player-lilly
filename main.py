"""
Lily Music Player — entry point.
Renamed from Bloomee. Same streaming engine, now with live synced lyrics.
"""

import sys
import os

# Make sure package root is on path when running from project dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_deps():
    missing = []
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        print(f"Install with:  pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    check_deps()

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Lily")
    app.setApplicationDisplayName("Lily 🌸")
    app.setOrganizationName("LilyMusic")

    # Apply global dark stylesheet
    from ui.styles import GLOBAL_STYLE
    app.setStyleSheet(GLOBAL_STYLE)

    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()