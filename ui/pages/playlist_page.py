"""Playlist page — displays and plays tracks in a local playlist."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor

from ui.widgets import ArtworkLabel, fmt_dur
from ui.styles import (TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
                       BG_HOVER, BG_SELECTED, BORDER)
from core.models import Track, Playlist


class PlaylistPage(QWidget):
    play_track    = pyqtSignal(object)        # Track
    queue_tracks  = pyqtSignal(list)           # list[Track]
    track_removed = pyqtSignal(int, int)       # playlist_id, position (1-indexed)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playlist_id: int | None = None
        self._tracks: list[Track]     = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        self._icon_lbl = QLabel("♫")
        self._icon_lbl.setStyleSheet(
            f"font-size: 42px; color: {ACCENT}; padding-right: 12px;")
        hdr_row.addWidget(self._icon_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        self._title_lbl = QLabel("Playlist")
        self._title_lbl.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {TEXT_PRIMARY};")
        self._meta_lbl = QLabel("")
        self._meta_lbl.setStyleSheet(
            f"font-size: 12px; color: {TEXT_MUTED};")
        info_col.addWidget(self._title_lbl)
        info_col.addWidget(self._meta_lbl)
        hdr_row.addLayout(info_col)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._play_all_btn = QPushButton("▶  Play All")
        self._play_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #0a0d15; border: none;
                border-radius: 20px; padding: 9px 24px; font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #9ef0b8; }}
        """)
        self._play_all_btn.clicked.connect(self._on_play_all)

        self._shuffle_btn = QPushButton("⇌  Shuffle")
        self._shuffle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 20px;
                padding: 9px 22px; font-size: 13px;
            }}
            QPushButton:hover {{ color: {TEXT_PRIMARY}; border-color: #2a2f42; }}
        """)
        self._shuffle_btn.clicked.connect(self._on_shuffle_all)

        btn_row.addWidget(self._play_all_btn)
        btn_row.addWidget(self._shuffle_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Track table ───────────────────────────────────────────────────────
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["#", "Title", "Artist", "Album", "Duration"])

        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 44)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 68)

        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(54)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(False)

        self._table.doubleClicked.connect(self._on_double_click)
        self._table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._ctx_menu)
        layout.addWidget(self._table, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, playlist: Playlist, tracks: list):
        self._playlist_id = playlist.id
        self._tracks = list(tracks)

        self._title_lbl.setText(playlist.name)
        n = len(tracks)
        total_sec = sum(t.duration for t in tracks)
        self._meta_lbl.setText(
            f"{n} track{'s' if n != 1 else ''}  ·  {fmt_dur(total_sec)}")

        self._table.setRowCount(0)
        for i, t in enumerate(tracks):
            self._table.insertRow(i)

            num = QTableWidgetItem(str(i + 1))
            num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setForeground(QColor(TEXT_MUTED))
            self._table.setItem(i, 0, num)

            self._table.setItem(i, 1, QTableWidgetItem(t.title))
            self._table.setItem(i, 2, QTableWidgetItem(t.artist))
            self._table.setItem(i, 3, QTableWidgetItem(t.album))

            dur = QTableWidgetItem(fmt_dur(t.duration))
            dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 4, dur)

    # ── Interactions ──────────────────────────────────────────────────────────

    def _on_double_click(self, idx):
        row = idx.row()
        if 0 <= row < len(self._tracks):
            self.play_track.emit(self._tracks[row])

    def _on_play_all(self):
        if self._tracks:
            self.queue_tracks.emit(list(self._tracks))

    def _on_shuffle_all(self):
        if self._tracks:
            import random
            shuffled = list(self._tracks)
            random.shuffle(shuffled)
            self.queue_tracks.emit(shuffled)

    def _ctx_menu(self, pos):
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            return
        menu = QMenu(self)
        play_act = QAction("▶  Play Now", self)
        play_act.triggered.connect(
            lambda: self.play_track.emit(self._tracks[rows[0]]))
        rem_act = QAction("Remove from Playlist", self)
        rem_act.triggered.connect(lambda: self._remove(rows[0]))
        menu.addAction(play_act)
        menu.addSeparator()
        menu.addAction(rem_act)
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _remove(self, row: int):
        if 0 <= row < len(self._tracks) and self._playlist_id is not None:
            self.track_removed.emit(self._playlist_id, row + 1)  # 1-indexed position
