"""Global stylesheet and color palette."""

ACCENT       = "#7ee8a2"
ACCENT_HOVER = "#9ef0b8"
BG           = "#0d0f17"
BG_CARD      = "#13161f"
BG_SIDEBAR   = "#111420"
BG_HOVER     = "#181b27"
BG_SELECTED  = "#1c2035"
BORDER       = "#1c2030"
TEXT_PRIMARY = "#e8eaf0"
TEXT_SECONDARY = "#6b7280"
TEXT_MUTED   = "#3d4258"


STYLESHEET = f"""
* {{
    font-family: 'Segoe UI', 'SF Pro Text', Arial, sans-serif;
    font-size: 13px;
    outline: none;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QWidget {{
    background: transparent;
    color: {TEXT_PRIMARY};
}}

/* ── Sidebar ── */
QWidget#sidebar {{
    background: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
}}
QLabel#logo {{
    font-size: 19px;
    font-weight: 700;
    color: {ACCENT};
    letter-spacing: 1px;
}}
QLabel#section_lbl {{
    font-size: 10px;
    font-weight: 600;
    color: {TEXT_MUTED};
    letter-spacing: 2px;
}}
QPushButton.nav_btn {{
    background: transparent;
    border: none;
    text-align: left;
    padding: 9px 14px;
    border-radius: 8px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QPushButton.nav_btn:hover {{
    background: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
QPushButton.nav_btn[active=true] {{
    background: {BG_SELECTED};
    color: {ACCENT};
    font-weight: 600;
}}
QListWidget#playlist_list {{
    background: transparent;
    border: none;
}}
QListWidget#playlist_list::item {{
    padding: 8px 14px;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QListWidget#playlist_list::item:hover {{
    background: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
QListWidget#playlist_list::item:selected {{
    background: {BG_SELECTED};
    color: {ACCENT};
}}

/* ── Content ── */
QWidget#content {{
    background: {BG};
}}
QWidget#topbar {{
    background: {BG};
    border-bottom: 1px solid {BORDER};
}}

/* ── Search ── */
QLineEdit#search {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 20px;
    padding: 8px 18px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QLineEdit#search:focus {{
    border-color: {ACCENT};
}}

/* ── Track Table ── */
QTableWidget {{
    background: transparent;
    border: none;
    selection-background-color: {BG_SELECTED};
    gridline-color: transparent;
}}
QTableWidget::item {{
    padding: 0 8px;
    border-bottom: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
}}
QTableWidget::item:hover {{ background: {BG_HOVER}; }}
QTableWidget::item:selected {{ background: {BG_SELECTED}; color: {TEXT_PRIMARY}; }}
QHeaderView::section {{
    background: {BG};
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    text-transform: uppercase;
}}
QHeaderView::section:hover {{ color: {ACCENT}; }}

/* ── Player Bar ── */
QWidget#player_bar {{
    background: #090c12;
    border-top: 1px solid {BORDER};
}}
QPushButton#play_btn {{
    background: {ACCENT};
    color: #0a0d15;
    border: none;
    border-radius: 22px;
    font-size: 18px;
    font-weight: 700;
    min-width: 44px;
    min-height: 44px;
}}
QPushButton#play_btn:hover {{ background: {ACCENT_HOVER}; }}
QPushButton.ctrl_btn {{
    background: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    font-size: 17px;
    border-radius: 18px;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton.ctrl_btn:hover {{ color: {TEXT_PRIMARY}; }}
QPushButton.ctrl_btn[active=true] {{ color: {ACCENT}; }}

/* ── Sliders ── */
QSlider#progress::groove:horizontal {{
    height: 4px; background: {BORDER}; border-radius: 2px;
}}
QSlider#progress::sub-page:horizontal {{
    background: {ACCENT}; border-radius: 2px;
}}
QSlider#progress::handle:horizontal {{
    width: 14px; height: 14px;
    background: {ACCENT}; border-radius: 7px; margin: -5px 0;
}}
QSlider#volume::groove:horizontal {{
    height: 3px; background: {BORDER}; border-radius: 2px;
}}
QSlider#volume::sub-page:horizontal {{
    background: {ACCENT}; border-radius: 2px;
}}
QSlider#volume::handle:horizontal {{
    width: 10px; height: 10px;
    background: {ACCENT}; border-radius: 5px; margin: -3.5px 0;
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: transparent; width: 6px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 3px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: #2a2f42; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}

/* ── Cards ── */
QWidget.card {{
    background: {BG_CARD};
    border-radius: 10px;
    border: 1px solid {BORDER};
}}
QWidget.card:hover {{
    background: {BG_HOVER};
    border-color: #252840;
}}

/* ── Buttons ── */
QPushButton.primary_btn {{
    background: {ACCENT};
    color: #0a0d15;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}}
QPushButton.primary_btn:hover {{ background: {ACCENT_HOVER}; }}
QPushButton.ghost_btn {{
    background: transparent;
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 7px 16px;
}}
QPushButton.ghost_btn:hover {{
    color: {TEXT_PRIMARY};
    border-color: #2a2f42;
}}

/* ── Context Menu ── */
QMenu {{
    background: {BG_CARD};
    border: 1px solid #252840;
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 4px;
    color: {TEXT_SECONDARY};
}}
QMenu::item:selected {{ background: {BG_SELECTED}; color: {ACCENT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* ── Misc ── */
QToolTip {{
    background: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid #252840;
    border-radius: 4px;
    padding: 4px 8px;
}}
QSplitter::handle {{ background: {BORDER}; width: 1px; }}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {ACCENT};
    border-bottom-color: {ACCENT};
}}
QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}
"""
GLOBAL_STYLE = STYLESHEET