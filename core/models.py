"""Shared data models."""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Track:
    id: Optional[int] = None          # DB id (local tracks only)
    source: str = "local"             # "local" | "saavn" | "youtube"
    source_id: str = ""               # saavn song id or youtube video id
    title: str = "Unknown"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration: float = 0.0
    image_url: str = ""
    stream_url: str = ""              # direct stream URL (filled on play)
    file_path: str = ""               # local path
    year: str = ""
    genre: str = ""
    play_count: int = 0
    artwork_data: Optional[bytes] = None  # embedded artwork bytes

    @property
    def display_duration(self) -> str:
        s = int(self.duration)
        return f"{s // 60}:{s % 60:02d}"

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "artwork_data"}


@dataclass
class Playlist:
    id: Optional[int] = None
    name: str = ""
    source: str = "local"             # "local" | "saavn"
    source_id: str = ""
    image_url: str = ""
    tracks: List[Track] = field(default_factory=list)
    track_count: int = 0
