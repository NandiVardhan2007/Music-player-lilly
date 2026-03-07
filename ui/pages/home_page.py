"""Home page — trending tracks and new releases from JioSaavn."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from ui.widgets import HorizontalScrollSection, TrackCard, SectionLabel
from ui.styles import TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT


class _FetchThread(QThread):
    charts_ready   = pyqtSignal(list)
    releases_ready = pyqtSignal(list)

    def run(self):
        try:
            from services.saavn import get_top_charts, get_new_releases
            charts   = get_top_charts()
            releases = get_new_releases()
        except Exception as e:
            print(f"[HomePage] fetch error: {e}")
            charts, releases = [], []
        self.charts_ready.emit(charts)
        self.releases_ready.emit(releases)


class HomePage(QWidget):
    play_track = pyqtSignal(object)   # Track

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fetch_thread = None
        self._build()
        self._load_content()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 30, 30, 0)
        outer.setSpacing(0)

        # Page header
        self._greeting = QLabel("Good evening 🌸")
        self._greeting.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {TEXT_PRIMARY}; padding-bottom: 4px;")
        outer.addWidget(self._greeting)

        sub = QLabel("What do you want to listen to?")
        sub.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY}; padding-bottom: 24px;")
        outer.addWidget(sub)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setSpacing(30)
        self._body_layout.setContentsMargins(0, 0, 16, 24)

        self._charts_section   = HorizontalScrollSection("Trending Now")
        self._releases_section = HorizontalScrollSection("New Releases")

        self._body_layout.addWidget(self._charts_section)
        self._body_layout.addWidget(self._releases_section)
        self._body_layout.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_content(self):
        """Kick off background fetch."""
        self._fetch_thread = _FetchThread()
        self._fetch_thread.charts_ready.connect(self._on_charts)
        self._fetch_thread.releases_ready.connect(self._on_releases)
        self._fetch_thread.start()

    def _on_charts(self, tracks: list):
        self._charts_section.clear()
        for t in tracks[:16]:
            card = TrackCard(t, size=156)
            card.clicked.connect(lambda _=None, tr=t: self.play_track.emit(tr))
            card.play_clicked.connect(lambda tr=t: self.play_track.emit(tr))
            self._charts_section.add_card(card)
        if not tracks:
            self._charts_section.clear()

    def _on_releases(self, tracks: list):
        self._releases_section.clear()
        for t in tracks[:16]:
            card = TrackCard(t, size=156)
            card.clicked.connect(lambda _=None, tr=t: self.play_track.emit(tr))
            card.play_clicked.connect(lambda tr=t: self.play_track.emit(tr))
            self._releases_section.add_card(card)

    def refresh(self):
        self._on_charts([])
        self._on_releases([])
        self._load_content()
