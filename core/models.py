"""Shared data models."""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Track:
    id: Optional[int] = None
    source: str = "local"
    source_id: str = ""
    title: str = "Unknown"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration: float = 0.0
    image_url: str = ""
    stream_url: str = ""
    file_path: str = ""
    year: str = ""
    genre: str = ""
    play_count: int = 0
    artwork_data: Optional[bytes] = None

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
    source: str = "local"
    source_id: str = ""
    image_url: str = ""
    tracks: List[Track] = field(default_factory=list)
    track_count: int = 0
