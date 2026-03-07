"""
JioSaavn unofficial API service.
Fetches song search results, charts, and decrypts stream URLs.
"""

import base64
import requests
import urllib.parse
from typing import List, Optional
from core.models import Track, Playlist

SAAVN_BASE = "https://www.jiosaavn.com/api.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}
TIMEOUT = 10


def _decrypt_url(enc: str) -> str:
    """Decrypt JioSaavn media URL using DES."""
    try:
        from Crypto.Cipher import DES
        key = b"38346591"
        cipher = DES.new(key, DES.MODE_ECB)
        decoded = base64.b64decode(enc)
        decrypted = cipher.decrypt(decoded)
        pad = decrypted[-1]
        url = decrypted[:-pad].decode("utf-8", errors="ignore")
        # Upgrade to 320kbps and https
        url = url.replace("_96.mp4", "_320.mp4")
        url = url.replace("http://", "https://")
        return url
    except ImportError:
        # pycryptodome not installed — return as-is (won't work but won't crash)
        return ""
    except Exception as e:
        print(f"[Saavn] decrypt error: {e}")
        return ""


def _parse_song(s: dict) -> Optional[Track]:
    """Parse a raw JioSaavn song dict into a Track."""
    try:
        enc = s.get("encrypted_media_url") or s.get("more_info", {}).get("encrypted_media_url", "")
        stream = _decrypt_url(enc) if enc else ""

        # Image — pick highest quality
        raw_img = s.get("image", "")
        image = raw_img.replace("150x150", "500x500").replace("50x50", "500x500")

        # Duration
        dur_raw = s.get("duration") or s.get("more_info", {}).get("duration", 0)
        try:
            duration = float(dur_raw)
        except (ValueError, TypeError):
            duration = 0.0

        # Artists
        artists = (s.get("primary_artists") or s.get("more_info", {}).get("primary_artists")
                   or s.get("singers") or "Unknown Artist")

        return Track(
            source="saavn",
            source_id=s.get("id") or s.get("songid") or "",
            title=s.get("song") or s.get("title") or "Unknown",
            artist=artists,
            album=s.get("album") or "",
            duration=duration,
            image_url=image,
            stream_url=stream,
            year=str(s.get("year") or ""),
        )
    except Exception as e:
        print(f"[Saavn] parse error: {e}")
        return None


def search_songs(query: str, n: int = 20, page: int = 1) -> List[Track]:
    """Search JioSaavn for songs."""
    try:
        params = {
            "__call": "search.getResults",
            "q": query,
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "n": n,
            "p": page,
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        songs = data.get("results") or []
        tracks = [_parse_song(s) for s in songs]
        return [t for t in tracks if t]
    except Exception as e:
        print(f"[Saavn] search error: {e}")
        return []


def get_stream_url(source_id: str) -> str:
    """Fetch and decrypt the stream URL for a given song ID."""
    try:
        params = {
            "__call": "song.getDetails",
            "cc": "in",
            "_marker": "0",
            "_format": "json",
            "pids": source_id,
            "api_version": "4",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        song = data.get(source_id) or {}
        enc = song.get("encrypted_media_url", "")
        return _decrypt_url(enc) if enc else ""
    except Exception as e:
        print(f"[Saavn] stream url error: {e}")
        return ""


def get_top_charts() -> List[Track]:
    """Fetch top trending songs from JioSaavn."""
    try:
        params = {
            "__call": "content.getAlbums",
            "album_id": "52253978",   # JioSaavn weekly top songs album
            "api_version": "4",
            "_format": "json",
            "_marker": "0",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        songs = data.get("songs") or data.get("list") or []
        tracks = [_parse_song(s) for s in songs]
        return [t for t in tracks if t]
    except Exception as e:
        print(f"[Saavn] charts error: {e}")
        # Fallback: search trending
        return search_songs("top hindi songs 2025", n=20)


def get_new_releases() -> List[Track]:
    """Fetch new releases."""
    try:
        params = {
            "__call": "search.getResults",
            "q": "new songs 2025",
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "n": "20",
            "p": "1",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        songs = data.get("results") or []
        tracks = [_parse_song(s) for s in songs]
        return [t for t in tracks if t]
    except Exception as e:
        print(f"[Saavn] new releases error: {e}")
        return []


def get_featured_playlists() -> List[dict]:
    """Fetch featured/curated playlists from JioSaavn."""
    try:
        params = {
            "__call": "search.getFeaturedPlaylists",
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "n": "10",
            "p": "1",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        playlists = data.get("results") or []
        result = []
        for p in playlists:
            img = (p.get("image") or "").replace("150x150", "500x500")
            result.append({
                "id": p.get("listid") or p.get("id") or "",
                "name": p.get("listname") or p.get("title") or "Playlist",
                "image_url": img,
                "count": p.get("count") or 0,
            })
        return result
    except Exception as e:
        print(f"[Saavn] playlists error: {e}")
        return []


def get_playlist_tracks(playlist_id: str) -> List[Track]:
    """Get tracks of a JioSaavn playlist."""
    try:
        params = {
            "__call": "playlist.getDetails",
            "listid": playlist_id,
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        songs = data.get("songs") or data.get("list") or []
        tracks = [_parse_song(s) for s in songs]
        return [t for t in tracks if t]
    except Exception as e:
        print(f"[Saavn] playlist tracks error: {e}")
        return []


def search_albums(query: str) -> List[dict]:
    """Search for albums."""
    try:
        params = {
            "__call": "search.getAlbumResults",
            "q": query,
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "n": "10",
            "p": "1",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        albums = data.get("results") or []
        result = []
        for a in albums:
            img = (a.get("image") or "").replace("150x150", "500x500")
            result.append({
                "id": a.get("albumid") or a.get("id") or "",
                "name": a.get("album") or a.get("title") or "Album",
                "artist": a.get("primary_artists") or a.get("music") or "",
                "image_url": img,
                "year": a.get("year") or "",
            })
        return result
    except Exception as e:
        print(f"[Saavn] album search error: {e}")
        return []
