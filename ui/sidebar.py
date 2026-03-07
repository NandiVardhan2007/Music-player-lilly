"""Left sidebar: navigation, playlists, add buttons."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from ui.styles import ACCENT, TEXT_SECONDARY, TEXT_MUTED, BG_CARD, BORDER
from core.models import Playlist


class Sidebar(QWidget):
    nav_home      = pyqtSignal()
    nav_search    = pyqtSignal()
    nav_library   = pyqtSignal()
    nav_queue     = pyqtSignal()
    nav_lyrics    = pyqtSignal()
    playlist_selected = pyqtSignal(int)
    playlist_created  = pyqtSignal(str)
    playlist_renamed  = pyqtSignal(int, str)
    playlist_deleted  = pyqtSignal(int)
    add_files  = pyqtSignal()
    add_folder = pyqtSignal()

    PAGES = ["home", "search", "library", "lyrics", "queue"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._btns = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 22, 14, 16)
        layout.setSpacing(0)

        logo = QLabel("🌸  Lily")
        logo.setObjectName("logo")
        layout.addWidget(logo)
        layout.addSpacing(26)

        for page, icon, label in [
            ("home",    "⌂",  "Home"),
            ("search",  "⌕",  "Search"),
            ("library", "♪",  "Library"),
            ("lyrics",  "✦",  "Lyrics"),
            ("queue",   "≡",  "Queue"),
        ]:
            btn = self._nav_button(f"{icon}  {label}", page)
            layout.addWidget(btn)
            self._btns[page] = btn
        layout.addSpacing(22)

        pl_row = QHBoxLayout()
        pl_lbl = QLabel("PLAYLISTS")
        pl_lbl.setObjectName("section_lbl")
        add_btn = QPushButton("+")
        add_btn.setFixedSize(20, 20)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {TEXT_MUTED}; background: transparent;
                border: none; font-size: 18px; font-weight: 300;
            }}
            QPushButton:hover {{ color: {ACCENT}; }}
        """)
        add_btn.setToolTip("New Playlist")
        add_btn.clicked.connect(self._on_create_playlist)
        pl_row.addWidget(pl_lbl)
        pl_row.addStretch()
        pl_row.addWidget(add_btn)
        layout.addLayout(pl_row)
        layout.addSpacing(6)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("playlist_list")
        self.playlist_list.itemClicked.connect(self._on_playlist_click)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_ctx)
        layout.addWidget(self.playlist_list, 1)
        layout.addSpacing(14)

        for label, sig in [("+ Add Files", self.add_files), ("+ Add Folder", self.add_folder)]:
            b = QPushButton(label)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: 1px dashed #252840;
                    border-radius: 6px; color: {TEXT_MUTED};
                    padding: 7px 10px; text-align: left; font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {ACCENT}; border-color: {ACCENT};
                    background: rgba(126,232,162,0.05);
                }}
            """)
            b.clicked.connect(sig.emit)
            layout.addWidget(b)
            layout.addSpacing(4)

        self._set_active("home")

    def _nav_button(self, text: str, page: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; text-align: left;
                padding: 9px 12px; border-radius: 8px;
                color: {TEXT_SECONDARY}; font-size: 13px;
            }}
            QPushButton:hover {{ background: #181b27; color: #e8eaf0; }}
        """)
        btn.clicked.connect(lambda: self._navigate(page))
        return btn

    def _navigate(self, page: str):
        self._set_active(page)
        getattr(self, f"nav_{page}").emit()
        self.playlist_list.clearSelection()

    def _set_active(self, page: str):
        for pg, btn in self._btns.items():
            active = pg == page
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#1c2035' if active else 'transparent'};
                    border: none; text-align: left;
                    padding: 9px 12px; border-radius: 8px;
                    color: {'#7ee8a2' if active else TEXT_SECONDARY};
                    font-size: 13px; font-weight: {'600' if active else 'normal'};
                }}
                QPushButton:hover {{
                    background: {'#1c2035' if active else '#181b27'};
                    color: {'#9ef0b8' if active else '#e8eaf0'};
                }}
            """)

    def load_playlists(self, playlists: list):
        self.playlist_list.clear()
        for pl in playlists:
            item = QListWidgetItem(f"  ♫  {pl.name}")
            item.setData(Qt.ItemDataRole.UserRole, pl.id)
            self.playlist_list.addItem(item)

    def _on_playlist_click(self, item):
        pid = item.data(Qt.ItemDataRole.UserRole)
        if pid:
            self._set_active("")
            self.playlist_selected.emit(pid)

    def _on_create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.playlist_created.emit(name.strip())

    def _playlist_ctx(self, pos):
        item = self.playlist_list.itemAt(pos)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename = QAction("Rename", self)
        delete = QAction("Delete", self)
        rename.triggered.connect(lambda: self._rename(pid))
        delete.triggered.connect(lambda: self.playlist_deleted.emit(pid))
        menu.addAction(rename)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.playlist_list.mapToGlobal(pos))

    def _rename(self, pid):
        name, ok = QInputDialog.getText(self, "Rename Playlist", "New name:")
        if ok and name.strip():
            self.playlist_renamed.emit(pid, name.strip())

    def highlight_playlist(self, pid: int):
        for i in range(self.playlist_list.count()):
            item = self.playlist_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == pid:
                self.playlist_list.setCurrentItem(item)
                return