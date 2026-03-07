"""Reusable track table used by Library, Playlist and Queue pages."""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from ui.styles import ACCENT, TEXT_SECONDARY, TEXT_MUTED, BG_SELECTED
from ui.widgets import fmt_dur
from core.models import Track


COLS = ["#", "Title", "Artist", "Album", "Duration", "Source"]
COL_W = {0: 36, 4: 65, 5: 72}


class TrackTable(QTableWidget):
    track_activated     = pyqtSignal(int)   # index in _tracks
    context_requested   = pyqtSignal(int, object)  # index, QPoint

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = []
        self._active_idx = -1
        self._setup()

    def _setup(self):
        self.setColumnCount(len(COLS))
        self.setHorizontalHeaderLabels(COLS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setDefaultSectionSize(50)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for col, w in COL_W.items():
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(col, w)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_ctx)
        self.doubleClicked.connect(self._on_double_click)

    def populate(self, tracks: list[Track]):
        self._tracks = tracks
        self._active_idx = -1
        self.setRowCount(0)
        for i, t in enumerate(tracks):
            self.insertRow(i)
            self._fill_row(i, t)

    def _fill_row(self, row: int, t: Track):
        num = QTableWidgetItem(str(row + 1))
        num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setForeground(QColor(TEXT_MUTED))
        self.setItem(row, 0, num)

        title = QTableWidgetItem(t.title or "")
        self.setItem(row, 1, title)

        artist = QTableWidgetItem(t.artist or "")
        artist.setForeground(QColor(TEXT_SECONDARY))
        self.setItem(row, 2, artist)

        album = QTableWidgetItem(t.album or "")
        album.setForeground(QColor(TEXT_SECONDARY))
        self.setItem(row, 3, album)

        dur = QTableWidgetItem(fmt_dur(t.duration))
        dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        dur.setForeground(QColor(TEXT_MUTED))
        self.setItem(row, 4, dur)

        src_map = {"local": "Local", "saavn": "JioSaavn", "youtube": "YouTube"}
        src = QTableWidgetItem(src_map.get(t.source, t.source))
        src.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        src.setForeground(QColor(TEXT_MUTED))
        self.setItem(row, 5, src)

    def highlight(self, idx: int):
        # Restore previous row
        if 0 <= self._active_idx < self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(self._active_idx, col)
                if item:
                    item.setBackground(QBrush())
                    if col == 1:
                        item.setForeground(QColor("#e8eaf0"))
        self._active_idx = idx
        if 0 <= idx < self.rowCount():
            for col in range(self.columnCount()):
                item = self.item(idx, col)
                if item:
                    item.setBackground(QBrush(QColor(BG_SELECTED)))
                    if col == 1:
                        item.setForeground(QColor(ACCENT))
            self.scrollToItem(self.item(idx, 1))

    def get_tracks(self) -> list[Track]:
        return self._tracks.copy()

    def _on_double_click(self, idx):
        self.track_activated.emit(idx.row())

    def _on_ctx(self, pos):
        row = self.rowAt(pos.y())
        if 0 <= row < len(self._tracks):
            self.context_requested.emit(row, self.mapToGlobal(pos))
