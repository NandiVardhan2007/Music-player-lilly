"""Shared reusable UI widgets."""

import io
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QLinearGradient

from ui.styles import ACCENT, BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER


class ArtworkLabel(QLabel):
    """Album artwork widget with rounded corners and placeholder."""

    def __init__(self, size: int = 54, radius: int = 8, parent=None):
        super().__init__(parent)
        self._sz = size
        self._radius = radius
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._show_placeholder()

    def _show_placeholder(self):
        pix = QPixmap(self._sz, self._sz)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(BG_CARD)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self._sz, self._sz, self._radius, self._radius)
        p.setPen(QPen(QColor(TEXT_MUTED)))
        p.setFont(QFont("Segoe UI Emoji", self._sz // 4))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        p.end()
        self.setPixmap(pix)

    def set_from_url(self, url: str):
        """Load artwork from a URL in background (non-blocking)."""
        if not url:
            self._show_placeholder()
            return
        try:
            import threading
            threading.Thread(target=self._fetch_url, args=(url,), daemon=True).start()
        except Exception:
            self._show_placeholder()

    def _fetch_url(self, url: str):
        try:
            import requests
            data = requests.get(url, timeout=6).content
            self._apply_image_data(data)
        except Exception:
            pass

    def set_from_bytes(self, data: bytes):
        if data:
            self._apply_image_data(data)
        else:
            self._show_placeholder()

    def _apply_image_data(self, data: bytes):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = img.resize((self._sz, self._sz), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "PNG")
            raw = buf.getvalue()
        except ImportError:
            raw = data

        from PyQt6.QtCore import QMetaObject, Qt as _Qt
        from PyQt6.QtGui import QPixmap as _QP
        pix = _QP()
        pix.loadFromData(raw)
        rounded = _QP(self._sz, self._sz)
        rounded.fill(QColor(0, 0, 0, 0))
        p = QPainter(rounded)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(pix.scaled(self._sz, self._sz,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self._sz, self._sz, self._radius, self._radius)
        p.end()
        # Must update on main thread
        try:
            self.setPixmap(rounded)
        except RuntimeError:
            pass


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(f"""
            font-size: 11px; font-weight: 700; color: {TEXT_MUTED};
            letter-spacing: 2px; padding: 4px 0;
        """)


class TrackCard(QWidget):
    """Compact clickable card for online search results / charts."""
    clicked = pyqtSignal()
    play_clicked = pyqtSignal()

    def __init__(self, track, size: int = 160, parent=None):
        super().__init__(parent)
        self.track = track
        self.setFixedWidth(size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.art = ArtworkLabel(size - 20, radius=6)
        if track.image_url:
            self.art.set_from_url(track.image_url)
        layout.addWidget(self.art)

        title = QLabel(track.title)
        title.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_PRIMARY};")
        title.setWordWrap(False)
        title.setMaximumWidth(size - 20)
        title.setToolTip(track.title)
        layout.addWidget(title)

        artist = QLabel(track.artist)
        artist.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        artist.setMaximumWidth(size - 20)
        layout.addWidget(artist)

        self.setStyleSheet(f"""
            TrackCard {{
                background: {BG_CARD};
                border-radius: 10px;
                border: 1px solid {BORDER};
            }}
            TrackCard:hover {{
                background: #181b27;
                border-color: #252840;
            }}
        """)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def mouseDoubleClickEvent(self, e):
        self.play_clicked.emit()


class HorizontalScrollSection(QWidget):
    """A labelled horizontal scrollable row of cards."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.label = SectionLabel(title)
        layout.addWidget(self.label)

        scroll_row = QHBoxLayout()
        scroll_row.setSpacing(12)
        scroll_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._row = scroll_row

        from PyQt6.QtWidgets import QScrollArea
        container = QWidget()
        container.setLayout(scroll_row)
        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(250)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll)

    def add_card(self, card: QWidget):
        self._row.addWidget(card)

    def clear(self):
        while self._row.count():
            item = self._row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


def fmt_dur(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"
