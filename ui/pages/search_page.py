"""Search page — search JioSaavn and YouTube for songs."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QScrollArea, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from ui.widgets import ArtworkLabel, fmt_dur
from ui.styles import (TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
                       BG_HOVER, BG_SELECTED, BORDER, BG_CARD)
from core.models import Track


# ── Background search thread ──────────────────────────────────────────────────

class _SearchThread(QThread):
    results_ready = pyqtSignal(list, str)   # (tracks, source_name)

    def __init__(self, query: str, source: str, parent=None):
        super().__init__(parent)
        self._query  = query
        self._source = source

    def run(self):
        try:
            if self._source == "saavn":
                from services.saavn import search_songs
                tracks = search_songs(self._query, n=25)
            else:  # youtube
                from services.youtube import search_songs
                tracks = search_songs(self._query, n=15)
            self.results_ready.emit(tracks, self._source)
        except Exception as e:
            print(f"[Search/{self._source}] {e}")
            self.results_ready.emit([], self._source)


# ── Single result row widget ──────────────────────────────────────────────────

class _ResultRow(QWidget):
    play_clicked = pyqtSignal(object)   # Track

    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self._track = track
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(60)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 16, 6)
        row.setSpacing(14)

        # Artwork
        self._art = ArtworkLabel(46, radius=6)
        if track.image_url:
            self._art.set_from_url(track.image_url)
        row.addWidget(self._art)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)

        title = QLabel(track.title)
        title.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {TEXT_PRIMARY};")
        title.setMaximumWidth(400)

        meta_parts = [track.artist]
        if track.album and track.album not in ("YouTube", "Unknown Album"):
            meta_parts.append(track.album)
        meta = QLabel("  ·  ".join(meta_parts))
        meta.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")

        info.addWidget(title)
        info.addWidget(meta)
        row.addLayout(info, 1)

        # Duration
        if track.duration > 0:
            dur = QLabel(fmt_dur(track.duration))
            dur.setStyleSheet(
                f"font-size: 11px; color: {TEXT_MUTED}; min-width: 40px;")
            dur.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(dur)

        self._normal_style = f"""
            _ResultRow, QWidget {{ background: transparent; border-radius: 6px; }}
        """
        self._hover_style = f"""
            _ResultRow, QWidget {{ background: {BG_HOVER}; border-radius: 6px; }}
        """

    def enterEvent(self, e):
        self.setStyleSheet(f"background: {BG_HOVER}; border-radius: 6px;")

    def leaveEvent(self, e):
        self.setStyleSheet("")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.play_clicked.emit(self._track)

    def mouseDoubleClickEvent(self, e):
        self.play_clicked.emit(self._track)


# ── Results pane (one per tab) ────────────────────────────────────────────────

class _ResultsPane(QWidget):
    """Scrollable list of _ResultRow widgets."""
    play_clicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")

        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setSpacing(1)
        self._vbox.setContentsMargins(0, 4, 0, 16)
        self._vbox.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def set_results(self, tracks: list):
        # Remove all except the stretch at end
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for t in tracks:
            row = _ResultRow(t)
            row.play_clicked.connect(self.play_clicked)
            self._vbox.insertWidget(self._vbox.count() - 1, row)

    def clear(self):
        self.set_results([])


# ── Search page ───────────────────────────────────────────────────────────────

class SearchPage(QWidget):
    play_track = pyqtSignal(object)   # Track

    def __init__(self, parent=None):
        super().__init__(parent)
        self._threads: list[_SearchThread] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(20)

        # Page header
        hdr = QLabel("Search")
        hdr.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(hdr)

        # Search bar row
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setPlaceholderText(
            "Search for songs, artists, albums…")
        self.search_input.setFixedHeight(42)
        self.search_input.returnPressed.connect(self._do_search)
        bar_row.addWidget(self.search_input, 1)

        self._search_btn = QPushButton("Search")
        self._search_btn.setFixedHeight(42)
        self._search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: #0a0d15; border: none;
                border-radius: 8px; padding: 0 22px; font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #9ef0b8; }}
            QPushButton:disabled {{ background: #3a4a3e; color: #6b7280; }}
        """)
        self._search_btn.clicked.connect(self._do_search)
        bar_row.addWidget(self._search_btn)
        layout.addLayout(bar_row)

        # Status label
        self._status = QLabel("Type to search JioSaavn and YouTube")
        self._status.setStyleSheet(
            f"font-size: 12px; color: {TEXT_MUTED};")
        layout.addWidget(self._status)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: transparent; color: #6b7280;
                padding: 9px 22px; border-bottom: 2px solid transparent;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #7ee8a2; border-bottom-color: #7ee8a2;
            }
            QTabBar::tab:hover { color: #e8eaf0; }
        """)

        self._saavn_pane = _ResultsPane()
        self._saavn_pane.play_clicked.connect(self.play_track)

        self._yt_pane = _ResultsPane()
        self._yt_pane.play_clicked.connect(self.play_track)

        self._tabs.addTab(self._saavn_pane, "🎵  JioSaavn")
        self._tabs.addTab(self._yt_pane,   "▶  YouTube")
        layout.addWidget(self._tabs, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    # ── Search logic ─────────────────────────────────────────────────────────

    def _do_search(self):
        q = self.search_input.text().strip()
        if not q:
            return
        # Cancel old threads
        for t in self._threads:
            if t.isRunning():
                t.quit()
        self._threads.clear()

        self._status.setText(f"Searching for \"{q}\"…")
        self._search_btn.setEnabled(False)
        self._saavn_pane.clear()
        self._yt_pane.clear()

        for source in ("saavn", "youtube"):
            thread = _SearchThread(q, source)
            thread.results_ready.connect(self._on_results)
            thread.finished.connect(lambda: self._search_btn.setEnabled(True))
            thread.start()
            self._threads.append(thread)

    def _on_results(self, tracks: list, source: str):
        pane = self._saavn_pane if source == "saavn" else self._yt_pane
        pane.set_results(tracks)
        count = len(tracks)
        self._status.setText(
            f"Found {count} result{'s' if count != 1 else ''} for "
            f"\"{self.search_input.text().strip()}\"" if count
            else f"No results found for \"{self.search_input.text().strip()}\"")
        self._search_btn.setEnabled(True)
