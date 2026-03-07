"""Library page — local music collection with scan, filter, and playback."""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView,
    QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QColor

from ui.widgets import fmt_dur
from ui.styles import (TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
                       BG_HOVER, BG_SELECTED, BORDER, BG_CARD)
from core.models import Track
from core.database import Database


# ── Background scanner ────────────────────────────────────────────────────────

class _ScanThread(QThread):
    track_scanned = pyqtSignal(object)   # Track
    progress      = pyqtSignal(int, int) # done, total
    finished      = pyqtSignal(int)      # total count

    AUDIO_EXT = {".mp3", ".flac", ".ogg", ".opus", ".m4a",
                 ".aac", ".wav", ".wma", ".mp4"}

    def __init__(self, paths: list, db: Database, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._db    = db
        self._stop  = False

    def run(self):
        files = []
        for p in self._paths:
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    for name in names:
                        if Path(name).suffix.lower() in self.AUDIO_EXT:
                            files.append(os.path.join(root, name))
            elif Path(p).suffix.lower() in self.AUDIO_EXT:
                files.append(p)

        for i, fp in enumerate(files):
            if self._stop:
                break
            self.progress.emit(i + 1, len(files))
            try:
                from core.metadata import read_metadata
                track = read_metadata(fp)
                tid   = self._db.upsert_local_track(track)
                track.id = tid
                self.track_scanned.emit(track)
            except Exception as e:
                print(f"[Scan] {fp}: {e}")

        self.finished.emit(len(files))

    def stop(self):
        self._stop = True


# ── Track table ───────────────────────────────────────────────────────────────

class TrackTable(QTableWidget):
    """Sortable table of local Tracks with context menu."""

    play_requested     = pyqtSignal(object)        # Track
    queue_requested    = pyqtSignal(list)           # list[Track]
    playlist_requested = pyqtSignal(object, list)  # Track, list[Playlist]

    HEADERS = ["#", "Title", "Artist", "Album", "Duration"]

    def __init__(self, db: Database, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self._db     = db
        self._tracks: list[Track] = []
        self._setup_table()

    def _setup_table(self):
        self.setHorizontalHeaderLabels(self.HEADERS)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 44)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(4, 68)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(54)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)

        self.doubleClicked.connect(self._on_double_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)

    # ── Data ──────────────────────────────────────────────────────────────────

    def load_tracks(self, tracks: list):
        self.setRowCount(0)
        self._tracks = list(tracks)
        self.setUpdatesEnabled(False)
        for t in tracks:
            self._append_row(t)
        self.setUpdatesEnabled(True)

    def add_track(self, track: Track):
        """Append a single track (used during scanning)."""
        if any(t.file_path == track.file_path for t in self._tracks):
            return   # already in table
        self._tracks.append(track)
        self._append_row(track)

    def _append_row(self, t: Track):
        row = self.rowCount()
        self.insertRow(row)

        num = QTableWidgetItem(str(row + 1))
        num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setForeground(QColor(TEXT_MUTED))
        self.setItem(row, 0, num)

        self.setItem(row, 1, QTableWidgetItem(t.title))
        self.setItem(row, 2, QTableWidgetItem(t.artist))
        self.setItem(row, 3, QTableWidgetItem(t.album))

        dur = QTableWidgetItem(fmt_dur(t.duration))
        dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, 4, dur)

    def get_tracks(self) -> list:
        return list(self._tracks)

    def highlight_track(self, track: Track):
        for row, t in enumerate(self._tracks):
            if t.file_path == track.file_path:
                self.selectRow(row)
                self.scrollTo(self.model().index(row, 0),
                              QAbstractItemView.ScrollHint.PositionAtCenter)
                return

    # ── Interactions ──────────────────────────────────────────────────────────

    def _on_double_click(self, idx):
        row = idx.row()
        if 0 <= row < len(self._tracks):
            self.play_requested.emit(self._tracks[row])

    def _selected_rows(self) -> list:
        return sorted({idx.row() for idx in self.selectedIndexes()})

    def _ctx_menu(self, pos):
        rows = self._selected_rows()
        if not rows:
            return
        menu = QMenu(self)
        play_act = QAction("▶  Play Now", self)
        play_act.triggered.connect(
            lambda: self.play_requested.emit(self._tracks[rows[0]]))
        queue_act = QAction(f"Add {len(rows)} track(s) to Queue", self)
        queue_act.triggered.connect(
            lambda: self.queue_requested.emit([self._tracks[r] for r in rows]))
        pl_act = QAction("Add to Playlist…", self)
        pl_act.triggered.connect(
            lambda: self.playlist_requested.emit(
                self._tracks[rows[0]], self._db.get_playlists()))

        menu.addAction(play_act)
        menu.addAction(queue_act)
        menu.addSeparator()
        menu.addAction(pl_act)
        menu.exec(self.viewport().mapToGlobal(pos))


# ── Library page ──────────────────────────────────────────────────────────────

class LibraryPage(QWidget):
    play_track      = pyqtSignal(object)        # Track
    queue_tracks    = pyqtSignal(list)           # list[Track]
    add_to_playlist = pyqtSignal(object, list)  # Track, list[Playlist]

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self._db          = db
        self._scan_thread = None
        self._build()
        self._load_from_db()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        title = QLabel("Library")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {TEXT_PRIMARY};")
        hdr_row.addWidget(title)
        hdr_row.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"font-size: 12px; color: {TEXT_MUTED};")
        hdr_row.addWidget(self._count_lbl)
        layout.addLayout(hdr_row)

        # ── Filter bar ────────────────────────────────────────────────────────
        self._filter = QLineEdit()
        self._filter.setObjectName("search")
        self._filter.setPlaceholderText("Filter by title, artist or album…")
        self._filter.setFixedHeight(36)
        self._filter.textChanged.connect(self._on_filter)
        layout.addWidget(self._filter)

        # ── Scan progress bar (hidden by default) ─────────────────────────────
        self._progress = QProgressBar()
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {BORDER}; border: none; border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background: {ACCENT}; border-radius: 1px;
            }}
        """)
        self._progress.hide()
        layout.addWidget(self._progress)

        # ── Status label (shows while scanning) ───────────────────────────────
        self._scan_lbl = QLabel("")
        self._scan_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED};")
        self._scan_lbl.hide()
        layout.addWidget(self._scan_lbl)

        # ── Track table ───────────────────────────────────────────────────────
        self.table = TrackTable(self._db)
        self.table.play_requested.connect(self.play_track)
        self.table.queue_requested.connect(self.queue_tracks)
        self.table.playlist_requested.connect(self.add_to_playlist)
        layout.addWidget(self.table, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_from_db(self):
        tracks = self._db.get_all_local_tracks()
        self.table.load_tracks(tracks)
        self._update_count(len(tracks))

    def _on_filter(self, text: str):
        tracks = self._db.get_all_local_tracks(search=text.strip() or None)
        self.table.load_tracks(tracks)
        self._update_count(len(tracks))

    def _update_count(self, n: int):
        self._count_lbl.setText(f"{n} track{'s' if n != 1 else ''}")

    # ── Scan ──────────────────────────────────────────────────────────────────

    def scan_paths(self, paths: list):
        """Start scanning files/folders and adding to the library."""
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.stop()

        self._progress.setRange(0, 0)   # indeterminate until count known
        self._progress.show()
        self._scan_lbl.setText("Scanning…")
        self._scan_lbl.show()

        self._scan_thread = _ScanThread(paths, self._db)
        self._scan_thread.track_scanned.connect(self._on_track_scanned)
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.finished.connect(self._on_scan_done)
        self._scan_thread.start()

    def _on_track_scanned(self, track: Track):
        self.table.add_track(track)

    def _on_scan_progress(self, done: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(done)
        self._scan_lbl.setText(f"Scanning… {done} / {total}")

    def _on_scan_done(self, count: int):
        self._progress.hide()
        self._scan_lbl.hide()
        self._update_count(self.table.rowCount())

    # ── Public API ────────────────────────────────────────────────────────────

    def highlight_track(self, track: Track):
        self.table.highlight_track(track)
