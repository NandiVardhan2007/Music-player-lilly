"""Queue page — shows the current playback queue."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QColor, QFont

from ui.widgets import fmt_dur
from ui.styles import (TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT,
                       BG_HOVER, BG_SELECTED, BORDER, BG_CARD)
from core.models import Track


class QueuePage(QWidget):
    play_at_index = pyqtSignal(int)
    remove_at     = pyqtSignal(int)
    clear_queue   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = []
        self._current_idx = -1
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 10)
        layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Queue")
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {TEXT_PRIMARY};")
        hdr.addWidget(title)
        hdr.addStretch()

        self._clear_btn = QPushButton("Clear Queue")
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; border-radius: 8px;
                padding: 7px 16px; font-size: 12px;
            }}
            QPushButton:hover {{ color: #e86a6a; border-color: #e86a6a; }}
        """)
        self._clear_btn.clicked.connect(self.clear_queue)
        hdr.addWidget(self._clear_btn)
        layout.addLayout(hdr)

        self._meta_lbl = QLabel("No tracks in queue")
        self._meta_lbl.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        layout.addWidget(self._meta_lbl)

        # ── List ──────────────────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent; border: none; outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {BORDER};
                padding: 0px;
            }}
            QListWidget::item:hover {{ background: {BG_HOVER}; }}
            QListWidget::item:selected {{ background: {BG_SELECTED}; }}
        """)
        self._list.setSpacing(0)
        self._list.setUniformItemSizes(True)
        self._list.doubleClicked.connect(
            lambda idx: self.play_at_index.emit(idx.row()))
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._ctx_menu)
        layout.addWidget(self._list, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_queue(self, tracks: list, current_idx: int):
        self._tracks      = list(tracks)
        self._current_idx = current_idx
        self._rebuild_list()

    def update_current(self, idx: int):
        self._current_idx = idx
        self._rebuild_list()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _rebuild_list(self):
        self._list.clear()
        for i, t in enumerate(self._tracks):
            active = (i == self._current_idx)
            prefix = "▶  " if active else f"{i + 1}.  "
            text   = f"{prefix}{t.title}  —  {t.artist}"
            dur    = fmt_dur(t.duration)

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 56))
            self._list.addItem(item)

            # Use a custom widget for each row
            row_widget = _QueueRow(i + 1, t, active)
            row_widget.play_clicked.connect(
                lambda _=None, idx=i: self.play_at_index.emit(idx))
            self._list.setItemWidget(item, row_widget)

        n = len(self._tracks)
        if n:
            total_sec = sum(t.duration for t in self._tracks)
            self._meta_lbl.setText(
                f"{n} track{'s' if n != 1 else ''}  ·  {fmt_dur(total_sec)} total")
        else:
            self._meta_lbl.setText("No tracks in queue")

    def _ctx_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        row = self._list.row(item)
        menu = QMenu(self)
        play_act   = QAction("▶  Play Now", self)
        remove_act = QAction("Remove", self)
        play_act.triggered.connect(lambda: self.play_at_index.emit(row))
        remove_act.triggered.connect(lambda: self.remove_at.emit(row))
        menu.addAction(play_act)
        menu.addSeparator()
        menu.addAction(remove_act)
        menu.exec(self._list.viewport().mapToGlobal(pos))


class _QueueRow(QWidget):
    """Single row widget inside the queue list."""
    play_clicked = pyqtSignal()

    def __init__(self, number: int, track: Track, active: bool, parent=None):
        super().__init__(parent)
        self._track = track
        self._active = active
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(14)

        # Index / playing indicator
        if active:
            idx_lbl = QLabel("▶")
            idx_lbl.setStyleSheet(f"font-size: 14px; color: {ACCENT}; min-width: 28px;")
        else:
            idx_lbl = QLabel(str(number))
            idx_lbl.setStyleSheet(
                f"font-size: 12px; color: {TEXT_MUTED}; min-width: 28px;")
        idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(idx_lbl)

        # Title + artist
        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)

        title_color = TEXT_PRIMARY if active else TEXT_SECONDARY
        title_lbl = QLabel(track.title)
        title_lbl.setStyleSheet(
            f"font-size: 13px; font-weight: {'600' if active else '400'}; "
            f"color: {title_color};")

        artist_lbl = QLabel(track.artist)
        artist_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED};")

        info.addWidget(title_lbl)
        info.addWidget(artist_lbl)
        row.addLayout(info, 1)

        # Duration
        dur_lbl = QLabel(fmt_dur(track.duration))
        dur_lbl.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED}; min-width: 42px;")
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(dur_lbl)

    def mouseDoubleClickEvent(self, e):
        self.play_clicked.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.play_clicked.emit()
