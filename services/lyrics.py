"""
Live lyrics service using lrclib.net
"""

import re
import requests
from typing import Optional, List
from dataclasses import dataclass, field

LRCLIB_BASE = "https://lrclib.net/api"
HEADERS = {
    "User-Agent": "LilyMusic/2.0 (https://github.com/lily-music)",
    "Accept": "application/json",
}
TIMEOUT = 8


@dataclass
class LyricLine:
    time_ms: int
    text: str

    @property
    def time_sec(self) -> float:
        return self.time_ms / 1000.0


@dataclass
class Lyrics:
    track_name:  str = ""
    artist_name: str = ""
    album_name:  str = ""
    duration:    float = 0.0
    synced:      List[LyricLine] = field(default_factory=list)
    plain:       str = ""
    source_id:   int = 0

    @property
    def has_synced(self) -> bool:
        return len(self.synced) > 0

    @property
    def has_plain(self) -> bool:
        return bool(self.plain.strip())

    @property
    def has_any(self) -> bool:
        return self.has_synced or self.has_plain


_LRC_RE = re.compile(r'\[(\d{1,3}):(\d{2})\.(\d{2,3})\](.*)')


def parse_lrc(lrc_text: str) -> List[LyricLine]:
    if not lrc_text:
        return []
    lines: List[LyricLine] = []
    for raw in lrc_text.splitlines():
        m = _LRC_RE.match(raw.strip())
        if not m:
            continue
        mins   = int(m.group(1))
        secs   = int(m.group(2))
        frac   = m.group(3)
        ms_frac = int(frac) * (10 if len(frac) == 2 else 1)
        text   = m.group(4).strip()
        time_ms = (mins * 60 + secs) * 1000 + ms_frac
        lines.append(LyricLine(time_ms=time_ms, text=text))
    lines.sort(key=lambda l: l.time_ms)
    return lines


def find_current_line(lines: List[LyricLine], position_ms: int) -> int:
    if not lines:
        return -1
    lo, hi, result = 0, len(lines) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if lines[mid].time_ms <= position_ms:
            result = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return result


def _build_lyrics(data: dict) -> Lyrics:
    return Lyrics(
        track_name  = data.get("trackName")   or "",
        artist_name = data.get("artistName")  or "",
        album_name  = data.get("albumName")   or "",
        duration    = float(data.get("duration") or 0),
        synced      = parse_lrc(data.get("syncedLyrics") or ""),
        plain       = data.get("plainLyrics") or "",
        source_id   = int(data.get("id") or 0),
    )


def _get_exact(title: str, artist: str,
               album: str = "", duration: float = 0) -> Optional[Lyrics]:
    params: dict = {"track_name": title, "artist_name": artist}
    if album:
        params["album_name"] = album
    if duration > 1:
        params["duration"] = int(duration)
    try:
        r = requests.get(f"{LRCLIB_BASE}/get", params=params,
                         headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, dict) and (data.get("syncedLyrics") or data.get("plainLyrics")):
                return _build_lyrics(data)
    except Exception as e:
        print(f"[Lyrics] GET error: {e}")
    return None


def _search(query: str, title: str = "", artist: str = "") -> list:
    params: dict = {"q": query}
    if title:
        params["track_name"] = title
    if artist:
        params["artist_name"] = artist
    try:
        r = requests.get(f"{LRCLIB_BASE}/search", params=params,
                         headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            results = r.json()
            return results if isinstance(results, list) else []
    except Exception as e:
        print(f"[Lyrics] search error: {e}")
    return []


_CLEAN_RE = re.compile(
    r'\((?:feat|ft|official|lyric|video|audio|hd|4k|live|remix)[^)]*\)'
    r'|\[(?:feat|ft|official|lyric|video|audio|hd|4k|live|remix)[^\]]*\]'
    r'|feat\..*|ft\.',
    re.IGNORECASE
)


def _clean(s: str) -> str:
    return _CLEAN_RE.sub("", s).strip(" -–—")


def get_lyrics(title: str, artist: str = "",
               album: str = "", duration: float = 0) -> Optional[Lyrics]:
    clean_title  = _clean(title)
    clean_artist = re.split(r',|&|feat\.|ft\.', artist, maxsplit=1, flags=re.I)[0].strip()

    if clean_title and clean_artist:
        result = _get_exact(clean_title, clean_artist, album, duration)
        if result:
            return result

    if clean_title and clean_artist:
        results = _search(f"{clean_title} {clean_artist}",
                          title=clean_title, artist=clean_artist)
        best = _pick_best(results)
        if best:
            return best

    if clean_title:
        results = _search(clean_title, title=clean_title)
        best = _pick_best(results)
        if best:
            return best

    return None


def _pick_best(results: list) -> Optional[Lyrics]:
    if not results:
        return None
    for item in results:
        if item.get("syncedLyrics"):
            return _build_lyrics(item)
    for item in results:
        if item.get("plainLyrics"):
            return _build_lyrics(item)
    return None
