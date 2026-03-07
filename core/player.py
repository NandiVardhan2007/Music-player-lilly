"""
Audio player using PyQt6.QtMultimedia.
Handles local files, HTTP stream URLs (JioSaavn, YouTube), and graceful fallback.
"""

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QObject, pyqtSignal
from core.models import Track


class Player(QObject):
    position_changed = pyqtSignal(float)   # seconds
    duration_changed = pyqtSignal(float)   # seconds
    state_changed    = pyqtSignal(str)     # "playing" | "paused" | "stopped"
    track_ended      = pyqtSignal()
    error_occurred   = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio  = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._volume = 0.7
        self._audio.setVolume(self._volume)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

        self._current_track: Track = None
        self._duration: float = 0

    # ── Playback control ─────────────────────────────────────────────────────

    def load_and_play(self, track: Track):
        """Load a track (local file or stream URL) and start playing."""
        self._current_track = track
        url = track.stream_url if track.source != "local" else track.file_path
        if not url:
            self.error_occurred.emit(f"No playable URL for: {track.title}")
            return
        if track.source == "local":
            self._player.setSource(QUrl.fromLocalFile(url))
        else:
            self._player.setSource(QUrl(url))
        self._player.play()

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def toggle(self):
        state = self._player.playbackState()
        from PyQt6.QtMultimedia import QMediaPlayer as QMP
        if state == QMP.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def seek(self, seconds: float):
        ms = int(seconds * 1000)
        self._player.setPosition(ms)

    def seek_fraction(self, fraction: float):
        if self._duration > 0:
            self.seek(fraction * self._duration)

    # ── Volume ───────────────────────────────────────────────────────────────

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))
        self._audio.setVolume(self._volume)

    def get_volume(self) -> float:
        return self._volume

    def mute(self, muted: bool):
        self._audio.setMuted(muted)

    # ── State queries ─────────────────────────────────────────────────────────

    def is_playing(self) -> bool:
        from PyQt6.QtMultimedia import QMediaPlayer as QMP
        return self._player.playbackState() == QMP.PlaybackState.PlayingState

    def is_paused(self) -> bool:
        from PyQt6.QtMultimedia import QMediaPlayer as QMP
        return self._player.playbackState() == QMP.PlaybackState.PausedState

    def position(self) -> float:
        return self._player.position() / 1000.0

    def duration(self) -> float:
        return self._duration

    # ── Internal slots ────────────────────────────────────────────────────────

    def _on_position(self, ms: int):
        self.position_changed.emit(ms / 1000.0)

    def _on_duration(self, ms: int):
        self._duration = ms / 1000.0
        self.duration_changed.emit(self._duration)

    def _on_state(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer as QMP
        if state == QMP.PlaybackState.PlayingState:
            self.state_changed.emit("playing")
        elif state == QMP.PlaybackState.PausedState:
            self.state_changed.emit("paused")
        else:
            self.state_changed.emit("stopped")

    def _on_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer as QMP
        if status == QMP.MediaStatus.EndOfMedia:
            self.track_ended.emit()

    def _on_error(self, error, msg):
        self.error_occurred.emit(f"Playback error: {msg}")
        print(f"[Player] error: {error} — {msg}")
