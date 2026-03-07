"""
Bloomee Music Player - Python/PyQt6 Replica
Requirements: pip install PyQt6 pygame mutagen Pillow
"""

import sys
import os
import sqlite3
import random
import time
import threading
from pathlib import Path

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3, APIC
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QListWidget, QListWidgetItem,
    QFileDialog, QInputDialog, QMessageBox, QSplitter, QFrame,
    QScrollArea, QLineEdit, QMenu, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QProgressBar, QAbstractItemView, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QDialogButtonBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, QPropertyAnimation,
    QEasingCurve, QRect, QMimeData
)
from PyQt6.QtGui import (
    QPixmap, QColor, QPainter, QPen, QBrush, QFont, QIcon,
    QLinearGradient, QPalette, QFontDatabase, QCursor, QAction,
    QDragEnterEvent, QDropEvent
)


# ─── Database ────────────────────────────────────────────────────────────────

class Database:
    def __init__(self, db_path="bloomee.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT,
                artist TEXT,
                album TEXT,
                duration REAL DEFAULT 0,
                track_number INTEGER,
                year TEXT,
                genre TEXT,
                play_count INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER,
                track_id INTEGER,
                position INTEGER,
                FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    def add_track(self, path, title, artist, album, duration, track_number=None, year=None, genre=None):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO tracks (path, title, artist, album, duration, track_number, year, genre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (path, title, artist, album, duration, track_number, year, genre))
        self.conn.commit()
        return c.lastrowid

    def get_all_tracks(self, search=None, sort_col="artist", sort_dir="ASC"):
        c = self.conn.cursor()
        cols = ["id", "path", "title", "artist", "album", "duration", "play_count", "year", "genre"]
        valid = {"title", "artist", "album", "duration", "play_count", "added_at"}
        if sort_col not in valid:
            sort_col = "artist"
        if search:
            c.execute(f"""
                SELECT {','.join(cols)} FROM tracks
                WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
                ORDER BY {sort_col} {sort_dir}
            """, (f"%{search}%", f"%{search}%", f"%{search}%"))
        else:
            c.execute(f"SELECT {','.join(cols)} FROM tracks ORDER BY {sort_col} {sort_dir}")
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def get_track_by_id(self, track_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM tracks WHERE id=?", (track_id,))
        row = c.fetchone()
        if row:
            cols = [desc[0] for desc in c.description]
            return dict(zip(cols, row))
        return None

    def increment_play_count(self, track_id):
        self.conn.execute("UPDATE tracks SET play_count = play_count + 1 WHERE id=?", (track_id,))
        self.conn.commit()

    def create_playlist(self, name):
        c = self.conn.cursor()
        c.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()
        return c.lastrowid

    def get_playlists(self):
        c = self.conn.cursor()
        c.execute("SELECT id, name FROM playlists ORDER BY name")
        return c.fetchall()

    def delete_playlist(self, playlist_id):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (playlist_id,))
        self.conn.commit()

    def rename_playlist(self, playlist_id, new_name):
        self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (new_name, playlist_id))
        self.conn.commit()

    def add_track_to_playlist(self, playlist_id, track_id):
        c = self.conn.cursor()
        c.execute("SELECT MAX(position) FROM playlist_tracks WHERE playlist_id=?", (playlist_id,))
        row = c.fetchone()
        pos = (row[0] or 0) + 1
        c.execute("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?,?,?)",
                  (playlist_id, track_id, pos))
        self.conn.commit()

    def get_playlist_tracks(self, playlist_id):
        c = self.conn.cursor()
        c.execute("""
            SELECT t.id, t.path, t.title, t.artist, t.album, t.duration, t.play_count
            FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        """, (playlist_id,))
        cols = ["id", "path", "title", "artist", "album", "duration", "play_count"]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def remove_track_from_playlist(self, playlist_id, track_id):
        self.conn.execute("DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?",
                          (playlist_id, track_id))
        self.conn.commit()

    def delete_track(self, track_id):
        self.conn.execute("DELETE FROM tracks WHERE id=?", (track_id,))
        self.conn.commit()

    def set_setting(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
        self.conn.commit()

    def get_setting(self, key, default=None):
        c = self.conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = c.fetchone()
        return row[0] if row else default


# ─── Metadata Reader ──────────────────────────────────────────────────────────

def get_audio_metadata(filepath):
    info = {
        "title": Path(filepath).stem,
        "artist": "Unknown Artist",
        "album": "Unknown Album",
        "duration": 0.0,
        "track_number": None,
        "year": None,
        "genre": None,
        "artwork": None,
    }
    if not MUTAGEN_AVAILABLE:
        return info
    try:
        audio = MutagenFile(filepath)
        if audio is None:
            return info
        # Duration
        if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
            info["duration"] = audio.info.length

        tags = audio.tags
        if tags is None:
            return info

        ext = Path(filepath).suffix.lower()

        if ext == ".mp3":
            def tag(key):
                v = tags.get(key)
                return str(v[0]) if v else None
            info["title"] = tag("TIT2") or info["title"]
            info["artist"] = tag("TPE1") or info["artist"]
            info["album"] = tag("TALB") or info["album"]
            info["year"] = tag("TDRC") or tag("TYER")
            info["genre"] = tag("TCON")
            tn = tag("TRCK")
            if tn:
                info["track_number"] = int(tn.split("/")[0]) if tn.split("/")[0].isdigit() else None
            for k, v in tags.items():
                if k.startswith("APIC"):
                    info["artwork"] = v.data
                    break

        elif ext in (".flac", ".ogg", ".opus"):
            def tag(key):
                v = tags.get(key.lower()) or tags.get(key.upper())
                return v[0] if v else None
            info["title"] = tag("title") or info["title"]
            info["artist"] = tag("artist") or info["artist"]
            info["album"] = tag("album") or info["album"]
            info["year"] = tag("date") or tag("year")
            info["genre"] = tag("genre")

        elif ext in (".m4a", ".mp4", ".aac"):
            def tag(key):
                v = tags.get(key)
                return str(v[0]) if v else None
            info["title"] = tag("©nam") or info["title"]
            info["artist"] = tag("©ART") or info["artist"]
            info["album"] = tag("©alb") or info["album"]
            info["year"] = tag("©day")
            info["genre"] = tag("©gen")
            covr = tags.get("covr")
            if covr:
                info["artwork"] = bytes(covr[0])

    except Exception:
        pass
    return info


def format_duration(seconds):
    if not seconds:
        return "0:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


# ─── Library Scanner Thread ───────────────────────────────────────────────────

class LibraryScanner(QThread):
    track_found = pyqtSignal(dict)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".mp4", ".aac", ".wav", ".wma"}

    def __init__(self, directories, db):
        super().__init__()
        self.directories = directories
        self.db = db
        self._stop = False

    def run(self):
        files = []
        for d in self.directories:
            for root, _, fnames in os.walk(d):
                for fn in fnames:
                    if Path(fn).suffix.lower() in self.EXTENSIONS:
                        files.append(os.path.join(root, fn))

        for i, fp in enumerate(files):
            if self._stop:
                break
            self.progress.emit(i + 1, len(files))
            meta = get_audio_metadata(fp)
            self.db.add_track(fp, meta["title"], meta["artist"], meta["album"],
                              meta["duration"], meta["track_number"], meta["year"], meta["genre"])
            self.track_found.emit(meta)
        self.finished.emit()

    def stop(self):
        self._stop = True


# ─── Audio Player ─────────────────────────────────────────────────────────────

class AudioPlayer:
    def __init__(self):
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self._length = 0
        self._start_time = 0
        self._pause_pos = 0
        self._volume = 0.7

        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)

    def load(self, filepath):
        self.stop()
        self.current_file = filepath
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.load(filepath)
                meta = get_audio_metadata(filepath)
                self._length = meta["duration"]
                return True
            except Exception as e:
                print(f"Load error: {e}")
                return False
        return False

    def play(self):
        if not PYGAME_AVAILABLE or not self.current_file:
            return
        pygame.mixer.music.play()
        self._start_time = time.time()
        self._pause_pos = 0
        self.is_playing = True
        self.is_paused = False

    def pause(self):
        if not PYGAME_AVAILABLE:
            return
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self._pause_pos = self.get_position()
            self.is_paused = True

    def resume(self):
        if not PYGAME_AVAILABLE:
            return
        if self.is_paused:
            pygame.mixer.music.unpause()
            self._start_time = time.time() - self._pause_pos
            self.is_paused = False

    def stop(self):
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self._pause_pos = 0

    def seek(self, seconds):
        if PYGAME_AVAILABLE and self.current_file:
            try:
                pygame.mixer.music.play(start=seconds)
                self._start_time = time.time() - seconds
                self._pause_pos = seconds
                if not self.is_playing:
                    self.is_playing = True
                    self.is_paused = False
            except Exception:
                pass

    def get_position(self):
        if not PYGAME_AVAILABLE:
            return 0
        try:
            pos = pygame.mixer.music.get_pos()
            if pos == -1:
                return 0
            return pos / 1000.0 + (self._pause_pos if self.is_paused else 0)
        except Exception:
            return 0

    def get_length(self):
        return self._length

    def set_volume(self, vol):
        self._volume = max(0.0, min(1.0, vol))
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(self._volume)

    def get_volume(self):
        return self._volume

    def is_ended(self):
        if not PYGAME_AVAILABLE:
            return False
        return self.is_playing and not self.is_paused and not pygame.mixer.music.get_busy()


# ─── Styles ───────────────────────────────────────────────────────────────────

STYLE = """
QMainWindow, QWidget#central {
    background: #0f1117;
}
QWidget {
    background: transparent;
    color: #e8eaf0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* Sidebar */
QWidget#sidebar {
    background: #13161f;
    border-right: 1px solid #1e2130;
}
QWidget#sidebar QLabel#logo {
    font-size: 20px;
    font-weight: 700;
    color: #7ee8a2;
    letter-spacing: 2px;
}
QWidget#sidebar QLabel#section_label {
    font-size: 10px;
    font-weight: 600;
    color: #4a5068;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Nav buttons */
QPushButton#nav_btn {
    background: transparent;
    border: none;
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    color: #6b7280;
}
QPushButton#nav_btn:hover {
    background: #1a1d2a;
    color: #c8ccd8;
}
QPushButton#nav_btn[active="true"] {
    background: #1e2235;
    color: #7ee8a2;
}

/* Playlist list */
QListWidget#playlist_list {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#playlist_list::item {
    padding: 8px 16px;
    border-radius: 6px;
    color: #6b7280;
    font-size: 12px;
}
QListWidget#playlist_list::item:hover {
    background: #1a1d2a;
    color: #c8ccd8;
}
QListWidget#playlist_list::item:selected {
    background: #1e2235;
    color: #7ee8a2;
}

/* Main content */
QWidget#content_area {
    background: #0f1117;
}

/* Search bar */
QLineEdit#search_bar {
    background: #1a1d2a;
    border: 1px solid #1e2130;
    border-radius: 20px;
    padding: 8px 16px;
    color: #e8eaf0;
    font-size: 13px;
}
QLineEdit#search_bar:focus {
    border: 1px solid #7ee8a2;
}
QLineEdit#search_bar::placeholder {
    color: #4a5068;
}

/* Track table */
QTableWidget {
    background: transparent;
    border: none;
    outline: none;
    gridline-color: transparent;
    selection-background-color: #1e2235;
}
QTableWidget::item {
    padding: 0px 8px;
    border-bottom: 1px solid #12151e;
    color: #9ba3b8;
}
QTableWidget::item:hover {
    background: #161928;
}
QTableWidget::item:selected {
    background: #1e2235;
    color: #e8eaf0;
}
QHeaderView::section {
    background: #0f1117;
    color: #4a5068;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid #1e2130;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    color: #7ee8a2;
}

/* Player bar */
QWidget#player_bar {
    background: #0c0e14;
    border-top: 1px solid #1e2130;
}

/* Control buttons */
QPushButton#ctrl_btn {
    background: transparent;
    border: none;
    color: #6b7280;
    font-size: 18px;
    border-radius: 20px;
    min-width: 40px;
    min-height: 40px;
}
QPushButton#ctrl_btn:hover {
    color: #e8eaf0;
}
QPushButton#play_btn {
    background: #7ee8a2;
    border: none;
    color: #0f1117;
    font-size: 20px;
    border-radius: 22px;
    min-width: 44px;
    min-height: 44px;
    font-weight: 700;
}
QPushButton#play_btn:hover {
    background: #9ef0b8;
}
QPushButton#ctrl_btn[active="true"] {
    color: #7ee8a2;
}

/* Progress slider */
QSlider#progress_slider::groove:horizontal {
    height: 4px;
    background: #1e2130;
    border-radius: 2px;
}
QSlider#progress_slider::handle:horizontal {
    width: 14px;
    height: 14px;
    background: #7ee8a2;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider#progress_slider::sub-page:horizontal {
    background: #7ee8a2;
    border-radius: 2px;
}
QSlider#progress_slider::handle:horizontal:hover {
    background: #9ef0b8;
}

/* Volume slider */
QSlider#vol_slider::groove:horizontal {
    height: 3px;
    background: #1e2130;
    border-radius: 2px;
}
QSlider#vol_slider::handle:horizontal {
    width: 10px;
    height: 10px;
    background: #7ee8a2;
    border-radius: 5px;
    margin: -3.5px 0;
}
QSlider#vol_slider::sub-page:horizontal {
    background: #7ee8a2;
    border-radius: 2px;
}

/* Scrollbar */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #1e2130;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #2a2f42;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0; }

/* Context menu */
QMenu {
    background: #1a1d2a;
    border: 1px solid #2a2f42;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 20px;
    border-radius: 4px;
    color: #c8ccd8;
}
QMenu::item:selected {
    background: #2a2f42;
    color: #7ee8a2;
}
QMenu::separator {
    height: 1px;
    background: #2a2f42;
    margin: 4px 8px;
}

/* Tooltip */
QToolTip {
    background: #1a1d2a;
    color: #e8eaf0;
    border: 1px solid #2a2f42;
    border-radius: 4px;
    padding: 4px 8px;
}
"""


# ─── Album Art Widget ─────────────────────────────────────────────────────────

class AlbumArtWidget(QLabel):
    def __init__(self, size=54):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_placeholder()

    def show_placeholder(self):
        pix = QPixmap(self._size, self._size)
        pix.fill(QColor("#1a1d2a"))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#2a2f42")))
        p.drawRoundedRect(0, 0, self._size, self._size, 8, 8)
        p.setPen(QPen(QColor("#4a5068")))
        p.setFont(QFont("Segoe UI", self._size // 4))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "♪")
        p.end()
        self.setPixmap(pix)

    def set_artwork(self, data: bytes):
        if not data or not PIL_AVAILABLE:
            self.show_placeholder()
            return
        try:
            img = Image.open(io.BytesIO(data))
            img = img.resize((self._size, self._size), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pix = QPixmap()
            pix.loadFromData(buf.getvalue())

            # Rounded corners
            rounded = QPixmap(self._size, self._size)
            rounded.fill(Qt.GlobalColor.transparent)
            p = QPainter(rounded)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setBrush(QBrush(pix))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 0, self._size, self._size, 8, 8)
            p.end()
            self.setPixmap(rounded)
        except Exception:
            self.show_placeholder()


# ─── Track Table ──────────────────────────────────────────────────────────────

class TrackTable(QTableWidget):
    track_activated = pyqtSignal(int)  # track db id
    context_menu_requested = pyqtSignal(int, QPoint)  # track id, pos

    COLS = ["#", "Title", "Artist", "Album", "Duration", "Plays"]

    def __init__(self):
        super().__init__()
        self.setColumnCount(len(self.COLS))
        self.setHorizontalHeaderLabels(self.COLS)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 40)
        self.setColumnWidth(4, 70)
        self.setColumnWidth(5, 55)
        self.verticalHeader().setDefaultSectionSize(48)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)
        self.doubleClicked.connect(self._on_double_click)
        self._track_ids = []
        self._current_row = -1

    def _on_double_click(self, index):
        row = index.row()
        if 0 <= row < len(self._track_ids):
            self.track_activated.emit(self._track_ids[row])

    def _on_context(self, pos):
        row = self.rowAt(pos.y())
        if 0 <= row < len(self._track_ids):
            self.context_menu_requested.emit(self._track_ids[row], self.mapToGlobal(pos))

    def populate(self, tracks):
        self._track_ids = []
        self.setRowCount(0)
        for i, t in enumerate(tracks):
            self._track_ids.append(t["id"])
            self.insertRow(i)
            num = QTableWidgetItem(str(i + 1))
            num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setForeground(QColor("#4a5068"))
            self.setItem(i, 0, num)
            self.setItem(i, 1, QTableWidgetItem(t.get("title") or ""))
            a2 = QTableWidgetItem(t.get("artist") or "")
            a2.setForeground(QColor("#6b7280"))
            self.setItem(i, 2, a2)
            a3 = QTableWidgetItem(t.get("album") or "")
            a3.setForeground(QColor("#6b7280"))
            self.setItem(i, 3, a3)
            dur = QTableWidgetItem(format_duration(t.get("duration", 0)))
            dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            dur.setForeground(QColor("#4a5068"))
            self.setItem(i, 4, dur)
            plays = QTableWidgetItem(str(t.get("play_count", 0)))
            plays.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            plays.setForeground(QColor("#4a5068"))
            self.setItem(i, 5, plays)

    def highlight_row(self, track_id):
        self._current_row = -1
        for i, tid in enumerate(self._track_ids):
            is_current = tid == track_id
            color = QColor("#1e2235") if is_current else QColor(0, 0, 0, 0)
            for col in range(self.columnCount()):
                item = self.item(i, col)
                if item:
                    item.setBackground(QBrush(color))
                    if is_current and col == 1:
                        item.setForeground(QColor("#7ee8a2"))
                    elif col in (2, 3, 4, 5):
                        item.setForeground(QColor("#4a5068" if not is_current else "#6b7280"))
            if is_current:
                self._current_row = i

    def get_track_ids(self):
        return self._track_ids.copy()

    def get_row_for_track(self, track_id):
        try:
            return self._track_ids.index(track_id)
        except ValueError:
            return -1


# ─── Player Bar ───────────────────────────────────────────────────────────────

class PlayerBar(QWidget):
    play_pause_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)
    volume_changed = pyqtSignal(float)
    shuffle_toggled = pyqtSignal(bool)
    repeat_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("player_bar")
        self.setFixedHeight(90)
        self._shuffle = False
        self._repeat = False
        self._dragging = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(0)

        # Left: artwork + track info
        left = QHBoxLayout()
        left.setSpacing(14)
        self.artwork = AlbumArtWidget(54)
        left.addWidget(self.artwork)

        info = QVBoxLayout()
        info.setSpacing(3)
        self.title_lbl = QLabel("No track selected")
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #e8eaf0;")
        self.title_lbl.setMaximumWidth(200)
        self.title_lbl.setWordWrap(False)
        self.artist_lbl = QLabel("")
        self.artist_lbl.setStyleSheet("font-size: 12px; color: #6b7280;")
        self.artist_lbl.setMaximumWidth(200)
        info.addWidget(self.title_lbl)
        info.addWidget(self.artist_lbl)
        left.addLayout(info)
        left.addStretch()

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(280)

        # Center: controls + progress
        center = QVBoxLayout()
        center.setSpacing(6)
        center.setContentsMargins(0, 12, 0, 10)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.shuffle_btn = QPushButton("⇌")
        self.shuffle_btn.setObjectName("ctrl_btn")
        self.shuffle_btn.setToolTip("Shuffle")
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("ctrl_btn")
        self.prev_btn.clicked.connect(self.prev_clicked)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.clicked.connect(self.play_pause_clicked)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("ctrl_btn")
        self.next_btn.clicked.connect(self.next_clicked)

        self.repeat_btn = QPushButton("↻")
        self.repeat_btn.setObjectName("ctrl_btn")
        self.repeat_btn.setToolTip("Repeat")
        self.repeat_btn.clicked.connect(self._toggle_repeat)

        for b in [self.shuffle_btn, self.prev_btn, self.play_btn, self.next_btn, self.repeat_btn]:
            controls.addWidget(b)

        progress = QHBoxLayout()
        progress.setSpacing(10)
        self.pos_lbl = QLabel("0:00")
        self.pos_lbl.setStyleSheet("font-size: 11px; color: #4a5068; min-width: 32px;")
        self.pos_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setObjectName("progress_slider")
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.sliderPressed.connect(lambda: setattr(self, '_dragging', True))
        self.progress.sliderReleased.connect(self._on_seek)

        self.dur_lbl = QLabel("0:00")
        self.dur_lbl.setStyleSheet("font-size: 11px; color: #4a5068; min-width: 32px;")

        progress.addWidget(self.pos_lbl)
        progress.addWidget(self.progress)
        progress.addWidget(self.dur_lbl)

        center.addLayout(controls)
        center.addLayout(progress)

        # Right: volume
        right = QHBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("font-size: 14px; color: #6b7280;")

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("vol_slider")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.valueChanged.connect(lambda v: self.volume_changed.emit(v / 100.0))

        right.addStretch()
        right.addWidget(vol_icon)
        right.addWidget(self.vol_slider)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setFixedWidth(200)

        layout.addWidget(left_w)
        layout.addStretch()
        layout.addLayout(center, 1)
        layout.addStretch()
        layout.addWidget(right_w)

    def _toggle_shuffle(self):
        self._shuffle = not self._shuffle
        self.shuffle_btn.setProperty("active", self._shuffle)
        self.shuffle_btn.style().unpolish(self.shuffle_btn)
        self.shuffle_btn.style().polish(self.shuffle_btn)
        self.shuffle_toggled.emit(self._shuffle)

    def _toggle_repeat(self):
        self._repeat = not self._repeat
        self.repeat_btn.setProperty("active", self._repeat)
        self.repeat_btn.style().unpolish(self.repeat_btn)
        self.repeat_btn.style().polish(self.repeat_btn)
        self.repeat_toggled.emit(self._repeat)

    def _on_seek(self):
        self._dragging = False
        val = self.progress.value() / 1000.0
        self.seek_requested.emit(val)

    def set_track(self, title, artist, artwork_data=None):
        self.title_lbl.setText(title or "No track")
        self.artist_lbl.setText(artist or "")
        self.title_lbl.setToolTip(title or "")
        if artwork_data:
            self.artwork.set_artwork(artwork_data)
        else:
            self.artwork.show_placeholder()

    def set_playing(self, playing):
        self.play_btn.setText("⏸" if playing else "▶")

    def update_position(self, pos, duration):
        if self._dragging or duration <= 0:
            return
        self.pos_lbl.setText(format_duration(pos))
        self.dur_lbl.setText(format_duration(duration))
        val = int((pos / duration) * 1000)
        self.progress.setValue(val)

    def set_duration(self, duration):
        self.dur_lbl.setText(format_duration(duration))


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.player = AudioPlayer()
        self._queue = []          # list of track IDs
        self._queue_index = -1
        self._shuffle = False
        self._repeat = False
        self._shuffle_history = []
        self._current_playlist_id = None
        self._scan_thread = None
        self._artwork_cache = {}

        self.setWindowTitle("Bloomee")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)
        self.setAcceptDrops(True)

        self._build_ui()
        self._setup_timer()
        self._load_library()
        self._load_playlists()

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Main splitter: sidebar + content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 24, 16, 16)
        sb_layout.setSpacing(0)

        logo = QLabel("🌸 Bloomee")
        logo.setObjectName("logo")
        sb_layout.addWidget(logo)
        sb_layout.addSpacing(28)

        lib_label = QLabel("LIBRARY")
        lib_label.setObjectName("section_label")
        sb_layout.addWidget(lib_label)
        sb_layout.addSpacing(8)

        self.nav_library = self._nav_btn("♪  Songs", True)
        self.nav_library.clicked.connect(lambda: self._nav_to("library"))
        sb_layout.addWidget(self.nav_library)
        sb_layout.addSpacing(20)

        pl_row = QHBoxLayout()
        pl_label = QLabel("PLAYLISTS")
        pl_label.setObjectName("section_label")
        add_pl_btn = QPushButton("+")
        add_pl_btn.setObjectName("ctrl_btn")
        add_pl_btn.setFixedSize(22, 22)
        add_pl_btn.setToolTip("New Playlist")
        add_pl_btn.clicked.connect(self._create_playlist)
        add_pl_btn.setStyleSheet("font-size: 16px; color: #4a5068; background: transparent; border: none;")
        pl_row.addWidget(pl_label)
        pl_row.addStretch()
        pl_row.addWidget(add_pl_btn)
        sb_layout.addLayout(pl_row)
        sb_layout.addSpacing(8)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("playlist_list")
        self.playlist_list.itemClicked.connect(self._on_playlist_clicked)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_context_menu)
        sb_layout.addWidget(self.playlist_list, 1)

        # Add files/folder buttons
        sb_layout.addSpacing(16)
        add_files_btn = self._sidebar_action_btn("+ Add Files")
        add_files_btn.clicked.connect(self._add_files)
        add_folder_btn = self._sidebar_action_btn("+ Add Folder")
        add_folder_btn.clicked.connect(self._add_folder)
        sb_layout.addWidget(add_files_btn)
        sb_layout.addSpacing(4)
        sb_layout.addWidget(add_folder_btn)

        # ── Content ──
        content = QWidget()
        content.setObjectName("content_area")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        self.page_title = QLabel("All Songs")
        self.page_title.setStyleSheet("font-size: 22px; font-weight: 700; color: #e8eaf0;")

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("search_bar")
        self.search_bar.setPlaceholderText("Search songs, artists, albums...")
        self.search_bar.setFixedWidth(280)
        self.search_bar.textChanged.connect(self._on_search)

        self.scan_progress = QLabel("")
        self.scan_progress.setStyleSheet("font-size: 11px; color: #4a5068;")

        h_layout.addWidget(self.page_title)
        h_layout.addStretch()
        h_layout.addWidget(self.scan_progress)
        h_layout.addSpacing(16)
        h_layout.addWidget(self.search_bar)

        c_layout.addWidget(header)

        # Track table
        self.table = TrackTable()
        self.table.track_activated.connect(self._play_track_by_id)
        self.table.context_menu_requested.connect(self._track_context_menu)
        c_layout.addWidget(self.table)

        splitter.addWidget(sidebar)
        splitter.addWidget(content)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

        # Player bar
        self.player_bar = PlayerBar()
        self.player_bar.play_pause_clicked.connect(self._toggle_play)
        self.player_bar.prev_clicked.connect(self._play_prev)
        self.player_bar.next_clicked.connect(self._play_next)
        self.player_bar.seek_requested.connect(self._on_seek)
        self.player_bar.volume_changed.connect(self.player.set_volume)
        self.player_bar.shuffle_toggled.connect(self._set_shuffle)
        self.player_bar.repeat_toggled.connect(self._set_repeat)
        root.addWidget(self.player_bar)

    def _nav_btn(self, text, active=False):
        b = QPushButton(text)
        b.setObjectName("nav_btn")
        b.setProperty("active", active)
        return b

    def _sidebar_action_btn(self, text):
        b = QPushButton(text)
        b.setObjectName("nav_btn")
        b.setStyleSheet("""
            QPushButton { color: #4a5068; text-align: left; padding: 8px 8px;
                          border: 1px dashed #2a2f42; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { color: #7ee8a2; border-color: #7ee8a2; }
        """)
        return b

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_to(self, view, playlist_id=None):
        self.nav_library.setProperty("active", view == "library")
        self.nav_library.style().unpolish(self.nav_library)
        self.nav_library.style().polish(self.nav_library)

        if view == "library":
            self._current_playlist_id = None
            self.page_title.setText("All Songs")
            self._load_library()
        elif view == "playlist" and playlist_id is not None:
            self._current_playlist_id = playlist_id
            for i in range(self.playlist_list.count()):
                item = self.playlist_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == playlist_id:
                    self.page_title.setText(item.text())
                    break
            self._load_playlist_tracks(playlist_id)

    # ── Library ───────────────────────────────────────────────────────────────

    def _load_library(self, search=None):
        tracks = self.db.get_all_tracks(search=search)
        self.table.populate(tracks)
        self._update_queue_from_table()
        if self._current_track_id():
            self.table.highlight_row(self._current_track_id())

    def _update_queue_from_table(self):
        self._queue = self.table.get_track_ids()

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add Audio Files", "",
            "Audio Files (*.mp3 *.flac *.ogg *.opus *.m4a *.aac *.wav *.wma)"
        )
        if files:
            self._import_files(files)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Music Folder")
        if folder:
            self._scan_directories([folder])

    def _import_files(self, files):
        count = 0
        for fp in files:
            meta = get_audio_metadata(fp)
            self.db.add_track(fp, meta["title"], meta["artist"], meta["album"],
                              meta["duration"], meta["track_number"], meta["year"], meta["genre"])
            count += 1
        self.scan_progress.setText(f"Added {count} track(s)")
        QTimer.singleShot(3000, lambda: self.scan_progress.setText(""))
        if self._current_playlist_id is None:
            self._load_library()

    def _scan_directories(self, dirs):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.stop()
        self._scan_thread = LibraryScanner(dirs, self.db)
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.finished.connect(self._on_scan_done)
        self._scan_thread.start()

    def _on_scan_progress(self, current, total):
        self.scan_progress.setText(f"Scanning {current}/{total}...")

    def _on_scan_done(self):
        self.scan_progress.setText("Scan complete")
        QTimer.singleShot(3000, lambda: self.scan_progress.setText(""))
        if self._current_playlist_id is None:
            self._load_library()

    def _on_search(self, text):
        if self._current_playlist_id is None:
            self._load_library(search=text if text else None)

    # ── Playlists ─────────────────────────────────────────────────────────────

    def _load_playlists(self):
        self.playlist_list.clear()
        for pid, name in self.db.get_playlists():
            item = QListWidgetItem(f"  ♫  {name}")
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self.playlist_list.addItem(item)

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.db.create_playlist(name.strip())
            self._load_playlists()

    def _on_playlist_clicked(self, item):
        pid = item.data(Qt.ItemDataRole.UserRole)
        if pid:
            self._nav_to("playlist", pid)

    def _load_playlist_tracks(self, playlist_id):
        tracks = self.db.get_playlist_tracks(playlist_id)
        self.table.populate(tracks)
        self._update_queue_from_table()
        if self._current_track_id():
            self.table.highlight_row(self._current_track_id())

    def _playlist_context_menu(self, pos):
        item = self.playlist_list.itemAt(pos)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename_act = QAction("Rename", self)
        delete_act = QAction("Delete", self)
        rename_act.triggered.connect(lambda: self._rename_playlist(pid))
        delete_act.triggered.connect(lambda: self._delete_playlist(pid))
        menu.addAction(rename_act)
        menu.addSeparator()
        menu.addAction(delete_act)
        menu.exec(self.playlist_list.mapToGlobal(pos))

    def _rename_playlist(self, pid):
        name, ok = QInputDialog.getText(self, "Rename Playlist", "New name:")
        if ok and name.strip():
            self.db.rename_playlist(pid, name.strip())
            self._load_playlists()
            if self._current_playlist_id == pid:
                self.page_title.setText(name.strip())

    def _delete_playlist(self, pid):
        self.db.delete_playlist(pid)
        self._load_playlists()
        if self._current_playlist_id == pid:
            self._nav_to("library")

    # ── Track Context Menu ────────────────────────────────────────────────────

    def _track_context_menu(self, track_id, pos):
        menu = QMenu(self)
        play_act = QAction("▶  Play Now", self)
        play_act.triggered.connect(lambda: self._play_track_by_id(track_id))
        menu.addAction(play_act)
        menu.addSeparator()

        # Add to playlist submenu
        add_to_pl = menu.addMenu("Add to Playlist")
        for pid, name in self.db.get_playlists():
            act = QAction(name, self)
            act.triggered.connect(lambda checked, p=pid: self.db.add_track_to_playlist(p, track_id))
            add_to_pl.addAction(act)
        if not self.db.get_playlists():
            add_to_pl.addAction(QAction("No playlists", self)).setEnabled(False)

        if self._current_playlist_id is not None:
            menu.addSeparator()
            remove_act = QAction("Remove from Playlist", self)
            remove_act.triggered.connect(lambda: self._remove_from_playlist(track_id))
            menu.addAction(remove_act)

        menu.addSeparator()
        del_act = QAction("Delete from Library", self)
        del_act.triggered.connect(lambda: self._delete_track(track_id))
        menu.addAction(del_act)
        menu.exec(pos)

    def _remove_from_playlist(self, track_id):
        if self._current_playlist_id:
            self.db.remove_track_from_playlist(self._current_playlist_id, track_id)
            self._load_playlist_tracks(self._current_playlist_id)

    def _delete_track(self, track_id):
        self.db.delete_track(track_id)
        self._load_library()

    # ── Playback ──────────────────────────────────────────────────────────────

    def _play_track_by_id(self, track_id):
        track = self.db.get_track_by_id(track_id)
        if not track:
            return
        if not os.path.exists(track["path"]):
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{track['path']}")
            return

        # Update queue index
        if track_id in self._queue:
            self._queue_index = self._queue.index(track_id)
        else:
            self._queue.append(track_id)
            self._queue_index = len(self._queue) - 1

        # Load and play
        if self.player.load(track["path"]):
            self.player.play()
            self.db.increment_play_count(track_id)

            # Update artwork
            meta = get_audio_metadata(track["path"])
            self.player_bar.set_track(track["title"], track["artist"], meta.get("artwork"))
            self.player_bar.set_duration(track["duration"])
            self.player_bar.set_playing(True)
            self.table.highlight_row(track_id)
            self.setWindowTitle(f"Bloomee — {track['title']}")
        else:
            if not PYGAME_AVAILABLE:
                QMessageBox.information(self, "pygame not installed",
                    "Install pygame to enable playback:\npip install pygame")

    def _toggle_play(self):
        if self.player.is_paused:
            self.player.resume()
            self.player_bar.set_playing(True)
        elif self.player.is_playing:
            self.player.pause()
            self.player_bar.set_playing(False)
        else:
            # Play first in queue
            if self._queue:
                idx = 0 if self._queue_index < 0 else self._queue_index
                self._play_track_by_id(self._queue[idx])

    def _play_next(self):
        if not self._queue:
            return
        if self._shuffle:
            idx = random.randint(0, len(self._queue) - 1)
        else:
            idx = (self._queue_index + 1) % len(self._queue)
        self._play_track_by_id(self._queue[idx])

    def _play_prev(self):
        if not self._queue:
            return
        pos = self.player.get_position()
        if pos > 3:
            self.player.seek(0)
            return
        if self._shuffle and self._shuffle_history:
            idx = self._shuffle_history.pop()
        else:
            idx = (self._queue_index - 1) % len(self._queue)
        self._play_track_by_id(self._queue[idx])

    def _on_seek(self, fraction):
        duration = self.player.get_length()
        if duration > 0:
            self.player.seek(fraction * duration)

    def _set_shuffle(self, val):
        self._shuffle = val

    def _set_repeat(self, val):
        self._repeat = val

    def _current_track_id(self):
        if 0 <= self._queue_index < len(self._queue):
            return self._queue[self._queue_index]
        return None

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _setup_timer(self):
        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if self.player.is_playing and not self.player.is_paused:
            pos = self.player.get_position()
            dur = self.player.get_length()
            self.player_bar.update_position(pos, dur)

            if self.player.is_ended():
                if self._repeat:
                    self.player.play()
                else:
                    self._play_next()

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        files = []
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                self._scan_directories([path])
                return
        if files:
            self._import_files(files)

    # ── Keyboard Shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key.Key_Space:
            self._toggle_play()
        elif key == Qt.Key.Key_Right:
            self._play_next()
        elif key == Qt.Key.Key_Left:
            self._play_prev()
        elif key == Qt.Key.Key_F and e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.search_bar.setFocus()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.player.stop()
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.stop()
            self._scan_thread.wait(2000)
        self.db.conn.close()
        e.accept()


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bloomee")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(STYLE)

    # Check deps
    missing = []
    if not PYGAME_AVAILABLE:
        missing.append("pygame")
    if not MUTAGEN_AVAILABLE:
        missing.append("mutagen")
    if not PIL_AVAILABLE:
        missing.append("Pillow")

    window = MainWindow()
    window.show()

    if missing:
        QMessageBox.information(
            window,
            "Optional dependencies missing",
            f"Install these for full functionality:\n\npip install {' '.join(missing)}\n\n"
            "The app will still open but some features may be limited."
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()