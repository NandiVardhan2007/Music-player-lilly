"""Lyrics page — live synced or plain lyrics for the playing track."""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from ui.styles import (TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
                       BG_CARD, BORDER, BG)
from core.models import Track


class LyricsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lyrics         = None
        self._current_idx    = -1
        self._line_labels: list[QLabel] = []
        self._build()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar: current track info ──
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(80)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(30, 14, 30, 14)
        topbar_layout.setSpacing(16)

        track_info = QVBoxLayout()
        track_info.setSpacing(3)
        self._track_lbl = QLabel("No track playing")
        self._track_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};")
        self._artist_lbl = QLabel("")
        self._artist_lbl.setStyleSheet(
            f"font-size: 12px; color: {TEXT_SECONDARY};")
        track_info.addWidget(self._track_lbl)
        track_info.addWidget(self._artist_lbl)
        topbar_layout.addLayout(track_info)
        topbar_layout.addStretch()

        self._src_lbl = QLabel("")
        self._src_lbl.setStyleSheet(
            f"font-size: 10px; color: {TEXT_MUTED}; letter-spacing: 1px;")
        topbar_layout.addWidget(self._src_lbl)
        outer.addWidget(topbar)

        # ── Scrollable lyric area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }")

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._body_layout.setContentsMargins(80, 48, 80, 80)
        self._body_layout.setSpacing(0)

        self._scroll.setWidget(self._body)
        outer.addWidget(self._scroll, 1)

        # Show initial placeholder
        self._show_message("Play a track to see lyrics ✦")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _clear_body(self):
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._line_labels = []

    def _show_message(self, text: str):
        self._clear_body()
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"font-size: 15px; color: {TEXT_MUTED}; padding: 60px 20px;")
        self._body_layout.addWidget(lbl)

    def _line_style(self, active: bool, empty: bool = False) -> str:
        if empty:
            return f"font-size: 10px; color: transparent; padding: 4px 0;"
        if active:
            return (
                f"font-size: 24px; font-weight: 700; color: {TEXT_PRIMARY};"
                f"padding: 12px 0; line-height: 1.4;"
            )
        return (
            f"font-size: 17px; font-weight: 400; color: {TEXT_MUTED};"
            f"padding: 8px 0; line-height: 1.4;"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def load_track(self, track: Track):
        """Called when a new track starts — fetches lyrics in background."""
        self._track_lbl.setText(track.title)
        self._artist_lbl.setText(track.artist)
        self._src_lbl.setText("")
        self._show_message("Loading lyrics…")
        self._lyrics      = None
        self._current_idx = -1
        threading.Thread(
            target=self._fetch_lyrics,
            args=(track,),
            daemon=True,
        ).start()

    def update_position(self, pos: float):
        """Called every ~250 ms with the playback position (seconds)."""
        if self._lyrics is None or not self._lyrics.has_synced:
            return

        from services.lyrics import find_current_line
        pos_ms = int(pos * 1000)
        idx    = find_current_line(self._lyrics.synced, pos_ms)

        if idx == self._current_idx:
            return

        # De-highlight previous line
        if 0 <= self._current_idx < len(self._line_labels):
            prev = self._line_labels[self._current_idx]
            is_empty = not self._lyrics.synced[self._current_idx].text.strip()
            prev.setStyleSheet(self._line_style(False, empty=is_empty))

        self._current_idx = idx

        # Highlight new line
        if 0 <= idx < len(self._line_labels):
            lbl = self._line_labels[idx]
            lbl.setStyleSheet(self._line_style(True))
            # Smooth scroll to keep active line near the vertical center
            QTimer.singleShot(
                0,
                lambda: self._scroll.ensureWidgetVisible(
                    lbl, 0, self._scroll.height() // 3)
            )

    # ── Background fetch ──────────────────────────────────────────────────────

    def _fetch_lyrics(self, track: Track):
        try:
            from services.lyrics import get_lyrics
            lyr = get_lyrics(
                track.title, track.artist,
                track.album, track.duration,
            )
        except Exception as e:
            print(f"[LyricsPage] fetch error: {e}")
            lyr = None
        # Marshal back to main thread
        QTimer.singleShot(0, lambda: self._apply_lyrics(lyr))

    def _apply_lyrics(self, lyr):
        if lyr is None or not lyr.has_any:
            self._show_message("No lyrics found for this track")
            return

        self._lyrics = lyr
        self._clear_body()

        if lyr.has_synced:
            self._src_lbl.setText("SYNCED  ·  LRCLIB.NET")
            for line in lyr.synced:
                empty = not line.text.strip()
                lbl   = QLabel(line.text if not empty else "·")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(self._line_style(False, empty=empty))
                lbl.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                self._body_layout.addWidget(lbl)
                self._line_labels.append(lbl)

        else:
            self._src_lbl.setText("PLAIN  ·  LRCLIB.NET")
            for raw_line in lyr.plain.splitlines():
                text  = raw_line.strip()
                empty = not text
                lbl   = QLabel(text if not empty else " ")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(self._line_style(False, empty=empty))
                lbl.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                self._body_layout.addWidget(lbl)
                self._line_labels.append(lbl)
