"""SQLite persistence layer."""
import sqlite3
import os
from pathlib import Path
from typing import List, Optional
from core.models import Track, Playlist


DB_PATH = Path(os.getenv("DB_PATH", str(Path.home() / ".lily" / "lily.db")))


class Database:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS tracks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT    DEFAULT 'local',
                source_id   TEXT    DEFAULT '',
                file_path   TEXT    UNIQUE,
                title       TEXT,
                artist      TEXT,
                album       TEXT,
                duration    REAL    DEFAULT 0,
                image_url   TEXT    DEFAULT '',
                year        TEXT    DEFAULT '',
                genre       TEXT    DEFAULT '',
                play_count  INTEGER DEFAULT 0,
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS playlists (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
                track_id    INTEGER REFERENCES tracks(id)    ON DELETE CASCADE,
                source      TEXT    DEFAULT 'local',
                source_id   TEXT    DEFAULT '',
                title       TEXT,
                artist      TEXT,
                album       TEXT,
                duration    REAL    DEFAULT 0,
                image_url   TEXT    DEFAULT '',
                file_path   TEXT    DEFAULT '',
                position    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT,
                source_id   TEXT,
                title       TEXT,
                artist      TEXT,
                image_url   TEXT,
                played_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    # ── Tracks ──────────────────────────────────────────────────────────────

    def upsert_local_track(self, t: Track) -> int:
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO tracks (source, source_id, file_path, title, artist, album,
                                duration, image_url, year, genre)
            VALUES ('local','',?,?,?,?,?,?,?,?)
            ON CONFLICT(file_path) DO UPDATE SET
                title=excluded.title, artist=excluded.artist, album=excluded.album,
                duration=excluded.duration, year=excluded.year, genre=excluded.genre
        """, (t.file_path, t.title, t.artist, t.album, t.duration,
              t.image_url, t.year, t.genre))
        self.conn.commit()
        if c.lastrowid:
            return c.lastrowid
        c.execute("SELECT id FROM tracks WHERE file_path=?", (t.file_path,))
        return c.fetchone()[0]

    def get_all_local_tracks(self, search: Optional[str] = None,
                              sort: str = "artist") -> List[Track]:
        valid = {"title", "artist", "album", "duration", "play_count", "added_at"}
        if sort not in valid:
            sort = "artist"
        q = "SELECT * FROM tracks WHERE source='local'"
        params = []
        if search:
            q += " AND (title LIKE ? OR artist LIKE ? OR album LIKE ?)"
            params = [f"%{search}%"] * 3
        q += f" ORDER BY {sort} ASC"
        rows = self.conn.execute(q, params).fetchall()
        return [self._row_to_track(r) for r in rows]

    def get_local_track(self, track_id: int) -> Optional[Track]:
        r = self.conn.execute("SELECT * FROM tracks WHERE id=?", (track_id,)).fetchone()
        return self._row_to_track(r) if r else None

    def increment_play_count(self, track_id: int):
        self.conn.execute("UPDATE tracks SET play_count=play_count+1 WHERE id=?", (track_id,))
        self.conn.commit()

    def delete_local_track(self, track_id: int):
        self.conn.execute("DELETE FROM tracks WHERE id=?", (track_id,))
        self.conn.commit()

    def _row_to_track(self, r) -> Track:
        return Track(
            id=r["id"], source=r["source"], source_id=r["source_id"],
            file_path=r["file_path"] or "", title=r["title"] or "Unknown",
            artist=r["artist"] or "Unknown Artist", album=r["album"] or "Unknown Album",
            duration=r["duration"] or 0, image_url=r["image_url"] or "",
            year=r["year"] or "", genre=r["genre"] or "", play_count=r["play_count"] or 0,
        )

    # ── Playlists ────────────────────────────────────────────────────────────

    def create_playlist(self, name: str) -> int:
        c = self.conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self.conn.commit()
        return c.lastrowid

    def get_playlists(self) -> List[Playlist]:
        rows = self.conn.execute("SELECT * FROM playlists ORDER BY name").fetchall()
        result = []
        for r in rows:
            count = self.conn.execute(
                "SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id=?", (r["id"],)
            ).fetchone()[0]
            result.append(Playlist(id=r["id"], name=r["name"], track_count=count))
        return result

    def rename_playlist(self, pid: int, name: str):
        self.conn.execute("UPDATE playlists SET name=? WHERE id=?", (name, pid))
        self.conn.commit()

    def delete_playlist(self, pid: int):
        self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self.conn.commit()

    def add_track_to_playlist(self, pid: int, track: Track):
        c = self.conn.execute(
            "SELECT MAX(position) FROM playlist_tracks WHERE playlist_id=?", (pid,))
        pos = (c.fetchone()[0] or 0) + 1
        self.conn.execute("""
            INSERT INTO playlist_tracks
              (playlist_id, track_id, source, source_id, title, artist, album,
               duration, image_url, file_path, position)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (pid, track.id, track.source, track.source_id, track.title,
              track.artist, track.album, track.duration, track.image_url,
              track.file_path, pos))
        self.conn.commit()

    def get_playlist_tracks(self, pid: int) -> List[Track]:
        rows = self.conn.execute("""
            SELECT * FROM playlist_tracks WHERE playlist_id=? ORDER BY position
        """, (pid,)).fetchall()
        tracks = []
        for r in rows:
            tracks.append(Track(
                id=r["track_id"], source=r["source"], source_id=r["source_id"],
                title=r["title"] or "Unknown", artist=r["artist"] or "Unknown Artist",
                album=r["album"] or "Unknown Album", duration=r["duration"] or 0,
                image_url=r["image_url"] or "", file_path=r["file_path"] or "",
            ))
        return tracks

    def remove_from_playlist(self, pid: int, position: int):
        self.conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id=? AND position=?", (pid, position))
        self.conn.commit()

    # ── History ──────────────────────────────────────────────────────────────

    def add_to_history(self, track: Track):
        self.conn.execute("""
            INSERT INTO history (source, source_id, title, artist, image_url)
            VALUES (?,?,?,?,?)
        """, (track.source, track.source_id, track.title, track.artist, track.image_url))
        self.conn.commit()

    def get_history(self, limit: int = 30) -> List[Track]:
        rows = self.conn.execute("""
            SELECT DISTINCT source, source_id, title, artist, image_url
            FROM history ORDER BY played_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [Track(source=r["source"], source_id=r["source_id"], title=r["title"],
                      artist=r["artist"], image_url=r["image_url"]) for r in rows]

    # ── Settings ─────────────────────────────────────────────────────────────

    def set(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, value))
        self.conn.commit()

    def get(self, key: str, default: str = "") -> str:
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r[0] if r else default
