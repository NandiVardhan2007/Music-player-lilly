"""Main application window — Lily Music Player."""

import os
import random
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QStackedWidget, QFileDialog, QInputDialog, QMessageBox, QLabel,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.sidebar import Sidebar
from ui.player_bar import PlayerBar
from ui.pages.home_page import HomePage
from ui.pages.search_page import SearchPage
from ui.pages.library_page import LibraryPage
from ui.pages.playlist_page import PlaylistPage
from ui.pages.queue_page import QueuePage
from ui.pages.lyrics_page import LyricsPage
from ui.styles import BG, BORDER
from core.player import Player
from core.database import Database
from core.models import Track, Playlist


class _StreamResolver(QThread):
    """Background thread to resolve stream URL before playing."""
    resolved = pyqtSignal(object, str)
    failed   = pyqtSignal(object, str)

    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self._track = track

    def run(self):
        t = self._track
        try:
            if t.source == "saavn":
                if t.stream_url:
                    self.resolved.emit(t, t.stream_url)
                    return
                from services.saavn import get_stream_url
                url = get_stream_url(t.source_id)
                if url:
                    self.resolved.emit(t, url)
                else:
                    self.failed.emit(t, "Could not get JioSaavn stream URL")
            elif t.source == "youtube":
                from services.youtube import get_stream_url
                url = get_stream_url(t.source_id)
                if url:
                    self.resolved.emit(t, url)
                else:
                    self.failed.emit(t, "Could not get YouTube stream URL")
            else:
                self.resolved.emit(t, t.file_path)
        except Exception as e:
            self.failed.emit(t, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.player = Player(self)
        self._queue: list[Track] = []
        self._queue_idx = -1
        self._shuffle = False
        self._repeat = False
        self._resolver: _StreamResolver = None

        self.setWindowTitle("Lily 🌸")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)
        self.setAcceptDrops(True)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._load_playlists()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")

        self.sidebar = Sidebar()

        self.stack = QStackedWidget()
        self.stack.setObjectName("content")

        self.home_page     = HomePage()
        self.search_page   = SearchPage()
        self.library_page  = LibraryPage(self.db)
        self.playlist_page = PlaylistPage()
        self.queue_page    = QueuePage()
        self.lyrics_page   = LyricsPage()   # ← NEW

        for page in [self.home_page, self.search_page, self.library_page,
                     self.playlist_page, self.queue_page, self.lyrics_page]:
            self.stack.addWidget(page)

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)

        self.player_bar = PlayerBar()

        root.addWidget(splitter, 1)
        root.addWidget(self.player_bar)

    # ── Signal Wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self):
        # Sidebar navigation
        self.sidebar.nav_home.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        self.sidebar.nav_search.connect(self._show_search)
        self.sidebar.nav_library.connect(lambda: self.stack.setCurrentWidget(self.library_page))
        self.sidebar.nav_queue.connect(self._show_queue)
        self.sidebar.nav_lyrics.connect(self._show_lyrics_page)   # ← NEW
        self.sidebar.playlist_selected.connect(self._show_playlist)
        self.sidebar.playlist_created.connect(self._create_playlist)
        self.sidebar.playlist_renamed.connect(lambda pid, n: (
            self.db.rename_playlist(pid, n), self._load_playlists()))
        self.sidebar.playlist_deleted.connect(lambda pid: (
            self.db.delete_playlist(pid), self._load_playlists(),
            self.stack.setCurrentWidget(self.home_page)))
        self.sidebar.add_files.connect(self._add_files)
        self.sidebar.add_folder.connect(self._add_folder)

        # Pages → play
        self.home_page.play_track.connect(self._play_online_track)
        self.search_page.play_track.connect(self._play_online_track)
        self.library_page.play_track.connect(self._play_local_track)
        self.library_page.queue_tracks.connect(self._enqueue_tracks)
        self.library_page.add_to_playlist.connect(self._add_to_playlist_dialog)
        self.playlist_page.play_track.connect(self._play_any_track)
        self.playlist_page.queue_tracks.connect(self._enqueue_tracks)
        self.playlist_page.track_removed.connect(
            lambda pid, pos: (self.db.remove_from_playlist(pid, pos),
                              self._refresh_playlist(pid)))
        self.queue_page.play_at_index.connect(self._play_queue_index)
        self.queue_page.remove_at.connect(self._remove_from_queue)
        self.queue_page.clear_queue.connect(self._clear_queue)

        # Player bar controls
        self.player_bar.play_pause.connect(self._toggle_play)
        self.player_bar.prev.connect(self._play_prev)
        self.player_bar.next.connect(self._play_next)
        self.player_bar.seek.connect(lambda f: self.player.seek_fraction(f))
        self.player_bar.volume.connect(self.player.set_volume)
        self.player_bar.shuffle_tog.connect(self._set_shuffle)
        self.player_bar.repeat_tog.connect(self._set_repeat)
        self.player_bar.queue_tog.connect(self._show_queue)

        # Player signals
        self.player.position_changed.connect(self._on_position)
        self.player.duration_changed.connect(self._on_duration)
        self.player.state_changed.connect(self._on_state)
        self.player.track_ended.connect(self._play_next)
        self.player.error_occurred.connect(
            lambda msg: self.statusBar().showMessage(f"⚠ {msg}", 5000))

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self).activated.connect(self._toggle_play)
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(self._play_next)
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(self._play_prev)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._show_search)
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(
            lambda: self.stack.setCurrentWidget(self.library_page))
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self._show_lyrics_page)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _show_search(self):
        self.stack.setCurrentWidget(self.search_page)
        self.search_page.focus_search()

    def _show_queue(self):
        self.stack.setCurrentWidget(self.queue_page)
        self.queue_page.update_queue(self._queue, self._queue_idx)

    def _show_lyrics_page(self):
        """Switch to the lyrics page."""
        self.stack.setCurrentWidget(self.lyrics_page)

    def _show_playlist(self, pid: int):
        tracks = self.db.get_playlist_tracks(pid)
        pl = next((p for p in self.db.get_playlists() if p.id == pid), None)
        if pl:
            pl.tracks = tracks
            self.playlist_page.load(pl, tracks)
            self.stack.setCurrentWidget(self.playlist_page)

    def _refresh_playlist(self, pid: int):
        self._show_playlist(pid)

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play_local_track(self, track: Track):
        if not os.path.exists(track.file_path):
            QMessageBox.warning(self, "File Not Found",
                                f"Cannot find:\n{track.file_path}")
            return
        all_tracks = self.library_page.table.get_tracks()
        if track in all_tracks:
            self._queue = all_tracks
            self._queue_idx = all_tracks.index(track)
        else:
            self._queue = [track]
            self._queue_idx = 0
        self._start_play(track)

    def _play_online_track(self, track: Track):
        self.statusBar().showMessage(f"⏳ Loading: {track.title}...", 0)
        self._queue = [track]
        self._queue_idx = 0
        self._resolve_and_play(track)

    def _play_any_track(self, track: Track):
        if track.source == "local":
            self._play_local_track(track)
        else:
            self._play_online_track(track)

    def _resolve_and_play(self, track: Track):
        if self._resolver and self._resolver.isRunning():
            self._resolver.quit()
        self._resolver = _StreamResolver(track)
        self._resolver.resolved.connect(self._on_resolved)
        self._resolver.failed.connect(self._on_resolve_failed)
        self._resolver.start()

    @pyqtSlot(object, str)
    def _on_resolved(self, track: Track, url: str):
        track.stream_url = url
        self._start_play(track)
        self.statusBar().clearMessage()

    @pyqtSlot(object, str)
    def _on_resolve_failed(self, track: Track, msg: str):
        self.statusBar().showMessage(f"⚠ Stream failed: {msg}", 6000)

    def _start_play(self, track: Track):
        self.player.load_and_play(track)
        self.player_bar.set_track(
            track.title, track.artist,
            image_url=track.image_url,
            artwork_bytes=track.artwork_data,
        )
        self.player_bar.set_duration(track.duration)
        self.setWindowTitle(f"Lily 🌸 — {track.title}")
        self.db.add_to_history(track)
        if track.id:
            self.db.increment_play_count(track.id)
        if track.source == "local":
            self.library_page.highlight_track(track)
        self.queue_page.update_current(self._queue_idx)

        # ── Lyrics: always fetch when a new track starts ──
        self.lyrics_page.load_track(track)

    def _toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
        elif self.player.is_paused():
            self.player.play()
        elif self._queue:
            idx = max(0, self._queue_idx)
            self._play_queue_index(idx)

    def _play_next(self):
        if not self._queue:
            return
        if self._shuffle:
            idx = random.randint(0, len(self._queue) - 1)
        else:
            idx = (self._queue_idx + 1) % len(self._queue)
        self._play_queue_index(idx)

    def _play_prev(self):
        if not self._queue:
            return
        if self.player.position() > 3:
            self.player.seek(0)
            return
        idx = (self._queue_idx - 1) % len(self._queue)
        self._play_queue_index(idx)

    def _play_queue_index(self, idx: int):
        if not (0 <= idx < len(self._queue)):
            return
        self._queue_idx = idx
        track = self._queue[idx]
        if track.source == "local":
            self._start_play(track)
        else:
            self._resolve_and_play(track)

    def _enqueue_tracks(self, tracks: list):
        self._queue = tracks
        self._queue_idx = 0
        self.queue_page.update_queue(tracks, 0)

    def _remove_from_queue(self, idx: int):
        if 0 <= idx < len(self._queue):
            self._queue.pop(idx)
            if self._queue_idx >= len(self._queue):
                self._queue_idx = len(self._queue) - 1
            self.queue_page.update_queue(self._queue, self._queue_idx)

    def _clear_queue(self):
        self._queue.clear()
        self._queue_idx = -1
        self.queue_page.update_queue([], -1)
        self.player.stop()

    def _set_shuffle(self, val: bool):
        self._shuffle = val

    def _set_repeat(self, val: bool):
        self._repeat = val

    # ── Player signal handlers ────────────────────────────────────────────────

    def _on_position(self, pos: float):
        dur = self.player.duration()
        self.player_bar.set_position(pos, dur)
        # ── Feed live position to lyrics page every tick ──
        self.lyrics_page.update_position(pos)

    def _on_duration(self, dur: float):
        self.player_bar.set_duration(dur)

    def _on_state(self, state: str):
        self.player_bar.set_playing(state == "playing")
        if state == "stopped" and self._repeat and self._queue:
            self._play_queue_index(self._queue_idx)

    # ── Library management ────────────────────────────────────────────────────

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio (*.mp3 *.flac *.ogg *.opus *.m4a *.aac *.wav *.wma)")
        if files:
            self.library_page.scan_paths(files)
            self.stack.setCurrentWidget(self.library_page)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Music Folder")
        if folder:
            self.library_page.scan_paths([folder])
            self.stack.setCurrentWidget(self.library_page)

    # ── Playlists ─────────────────────────────────────────────────────────────

    def _load_playlists(self):
        pls = self.db.get_playlists()
        self.sidebar.load_playlists(pls)

    def _create_playlist(self, name: str):
        self.db.create_playlist(name)
        self._load_playlists()

    def _add_to_playlist_dialog(self, track: Track, playlists: list):
        if not playlists:
            name, ok = QInputDialog.getText(self, "Create Playlist",
                                            "No playlists yet. Name:")
            if ok and name.strip():
                pid = self.db.create_playlist(name.strip())
                pl = Playlist(id=pid, name=name.strip())
                self.db.add_track_to_playlist(pid, track)
                self._load_playlists()
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Add to Playlist")
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        lbl = QLabel(f"Add \"{track.title}\" to:")
        lbl.setStyleSheet("color: #e8eaf0;")
        layout.addWidget(lbl)
        lst = QListWidget()
        lst.setStyleSheet("background: #13161f; color: #9ba3b8; border: none;")
        for pl in playlists:
            item = QListWidgetItem(pl.name)
            item.setData(Qt.ItemDataRole.UserRole, pl.id)
            lst.addItem(item)
        layout.addWidget(lst)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.setStyleSheet("QDialog { background: #0f1117; }")
        if dlg.exec() == QDialog.DialogCode.Accepted and lst.currentItem():
            pid = lst.currentItem().data(Qt.ItemDataRole.UserRole)
            self.db.add_track_to_playlist(pid, track)
            self.statusBar().showMessage("Added to playlist ✓", 3000)

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        files = [p for p in paths if os.path.isfile(p)]
        dirs  = [p for p in paths if os.path.isdir(p)]
        if files or dirs:
            self.library_page.scan_paths(files + dirs)
            self.stack.setCurrentWidget(self.library_page)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space and not self.search_page.search_input.hasFocus():
            self._toggle_play()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.player.stop()
        if self._resolver and self._resolver.isRunning():
            self._resolver.quit()
            self._resolver.wait(1000)
        self.db.conn.close()
        e.accept()