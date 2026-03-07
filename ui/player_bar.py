"""Bottom player control bar."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from ui.widgets import ArtworkLabel, fmt_dur
from ui.styles import TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED


class PlayerBar(QWidget):
    play_pause  = pyqtSignal()
    prev        = pyqtSignal()
    next        = pyqtSignal()
    seek        = pyqtSignal(float)        # fraction 0-1
    volume      = pyqtSignal(float)        # 0-1
    shuffle_tog = pyqtSignal(bool)
    repeat_tog  = pyqtSignal(bool)
    queue_tog   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("player_bar")
        self.setFixedHeight(92)
        self._shuffle = False
        self._repeat  = False
        self._seeking = False
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 0, 20, 0)
        root.setSpacing(0)

        # ── Left: now playing ──
        left = QHBoxLayout()
        left.setSpacing(14)
        self.art = ArtworkLabel(58, radius=8)
        left.addWidget(self.art)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.lbl_title = QLabel("Not Playing")
        self.lbl_title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY};")
        self.lbl_title.setMaximumWidth(210)
        self.lbl_artist = QLabel("")
        self.lbl_artist.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        self.lbl_artist.setMaximumWidth(210)
        info.addStretch()
        info.addWidget(self.lbl_title)
        info.addWidget(self.lbl_artist)
        info.addStretch()
        left.addLayout(info)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(290)

        # ── Center: controls + progress ──
        center = QVBoxLayout()
        center.setSpacing(8)
        center.setContentsMargins(0, 12, 0, 10)

        ctrls = QHBoxLayout()
        ctrls.setSpacing(6)
        ctrls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_shuffle = self._ctrl_btn("⇌", "Shuffle")
        self.btn_shuffle.clicked.connect(self._on_shuffle)
        self.btn_prev    = self._ctrl_btn("⏮", "Previous")
        self.btn_prev.clicked.connect(self.prev)
        self.btn_play    = QPushButton("▶")
        self.btn_play.setObjectName("play_btn")
        self.btn_play.setFixedSize(44, 44)
        self.btn_play.clicked.connect(self.play_pause)
        self.btn_next    = self._ctrl_btn("⏭", "Next")
        self.btn_next.clicked.connect(self.next)
        self.btn_repeat  = self._ctrl_btn("↻", "Repeat")
        self.btn_repeat.clicked.connect(self._on_repeat)

        for b in [self.btn_shuffle, self.btn_prev, self.btn_play,
                  self.btn_next, self.btn_repeat]:
            ctrls.addWidget(b)

        # Progress row
        prog = QHBoxLayout()
        prog.setSpacing(10)
        self.lbl_pos = QLabel("0:00")
        self.lbl_pos.setStyleSheet(
            f"font-size: 11px; color: {TEXT_MUTED}; min-width: 34px;")
        self.lbl_pos.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("progress")
        self.slider.setRange(0, 10000)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.slider.sliderReleased.connect(self._on_seek_release)
        self.lbl_dur = QLabel("0:00")
        self.lbl_dur.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; min-width: 34px;")
        prog.addWidget(self.lbl_pos)
        prog.addWidget(self.slider)
        prog.addWidget(self.lbl_dur)

        center.addLayout(ctrls)
        center.addLayout(prog)

        # ── Right: volume + queue ──
        right = QHBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(8)

        self.btn_queue = self._ctrl_btn("≡", "Queue")
        self.btn_queue.clicked.connect(self.queue_tog)

        lbl_vol = QLabel("🔊")
        lbl_vol.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("volume")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(88)
        self.vol_slider.valueChanged.connect(lambda v: self.volume.emit(v / 100.0))

        right.addStretch()
        right.addWidget(self.btn_queue)
        right.addSpacing(4)
        right.addWidget(lbl_vol)
        right.addWidget(self.vol_slider)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setFixedWidth(200)

        root.addWidget(left_w)
        root.addStretch()
        root.addLayout(center, 1)
        root.addStretch()
        root.addWidget(right_w)

    def _ctrl_btn(self, text: str, tip: str = "") -> QPushButton:
        b = QPushButton(text)
        b.setProperty("class", "ctrl_btn")
        b.setProperty("active", False)
        b.setToolTip(tip)
        b.setFixedSize(36, 36)
        b.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {TEXT_SECONDARY}; font-size: 17px; border-radius: 18px;
            }}
            QPushButton:hover {{ color: #e8eaf0; }}
            QPushButton[active=true] {{ color: #7ee8a2; }}
        """)
        return b

    # ── Public API ────────────────────────────────────────────────────────────

    def set_track(self, title: str, artist: str,
                  image_url: str = "", artwork_bytes: bytes = None):
        self.lbl_title.setText(title or "Unknown")
        self.lbl_artist.setText(artist or "")
        self.lbl_title.setToolTip(title or "")
        if artwork_bytes:
            self.art.set_from_bytes(artwork_bytes)
        elif image_url:
            self.art.set_from_url(image_url)
        else:
            self.art._show_placeholder()

    def set_playing(self, playing: bool):
        self.btn_play.setText("⏸" if playing else "▶")

    def set_position(self, pos: float, dur: float):
        if self._seeking or dur <= 0:
            return
        self.lbl_pos.setText(fmt_dur(pos))
        self.lbl_dur.setText(fmt_dur(dur))
        val = int((pos / dur) * 10000)
        self.slider.setValue(val)

    def set_duration(self, dur: float):
        self.lbl_dur.setText(fmt_dur(dur))

    def set_volume_value(self, vol: float):
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(int(vol * 100))
        self.vol_slider.blockSignals(False)

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_shuffle(self):
        self._shuffle = not self._shuffle
        self._set_active(self.btn_shuffle, self._shuffle)
        self.shuffle_tog.emit(self._shuffle)

    def _on_repeat(self):
        self._repeat = not self._repeat
        self._set_active(self.btn_repeat, self._repeat)
        self.repeat_tog.emit(self._repeat)

    def _on_seek_release(self):
        self._seeking = False
        frac = self.slider.value() / 10000.0
        self.seek.emit(frac)

    def _set_active(self, btn: QPushButton, active: bool):
        style = f"""
            QPushButton {{
                background: transparent; border: none;
                color: {'#7ee8a2' if active else '#6b7280'};
                font-size: 17px; border-radius: 18px;
            }}
            QPushButton:hover {{ color: {'#9ef0b8' if active else '#e8eaf0'}; }}
        """
        btn.setStyleSheet(style)
