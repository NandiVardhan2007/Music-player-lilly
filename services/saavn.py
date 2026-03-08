"""
JioSaavn unofficial API service — fixed stream URL resolution.
"""

import base64
import requests
from typing import List, Optional
from core.models import Track

SAAVN_BASE = "https://www.jiosaavn.com/api.php"
SAAVN_API  = "https://saavn.dev/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.jiosaavn.com/",
}
TIMEOUT = 12


def _decrypt_url(enc: str) -> str:
    """Decrypt JioSaavn DES-ECB encrypted media URL."""
    if not enc:
        return ""
    try:
        from Crypto.Cipher import DES
        key = b"38346591"
        cipher = DES.new(key, DES.MODE_ECB)
        missing = len(enc) % 4
        if missing:
            enc += "=" * (4 - missing)
        decoded = base64.b64decode(enc)
        decrypted = cipher.decrypt(decoded)
        pad = decrypted[-1]
        if 1 <= pad <= 8:
            decrypted = decrypted[:-pad]
        url = decrypted.decode("utf-8", errors="ignore").strip()
        url = url.replace("http://", "https://")
        print(f"[Saavn] decrypted: {url[:80]}")
        return url
    except ImportError:
        print("[Saavn] pycryptodome not installed — pip install pycryptodome")
        return ""
    except Exception as e:
        print(f"[Saavn] decrypt error: {e}")
        return ""


def _pick_quality(url: str, quality: str = "320") -> str:
    """Swap quality suffix in CDN URL."""
    if not url:
        return url
    for q in ("320", "160", "96"):
        url = url.replace(f"_{q}.mp4", f"_{quality}.mp4")
    return url


def _parse_song(s: dict) -> Optional[Track]:
    try:
        enc = (s.get("encrypted_media_url")
               or s.get("more_info", {}).get("encrypted_media_url")
               or "")

        direct_url = ""
        if s.get("download_url"):
            urls = s["download_url"]
            if isinstance(urls, list) and urls:
                best = sorted(urls, key=lambda x: int(x.get("quality","0").replace("kbps","")), reverse=True)
                direct_url = best[0].get("url", "")
        elif s.get("media_url"):
            direct_url = s["media_url"]

        stream = direct_url or (_decrypt_url(enc) if enc else "")
        if stream:
            stream = _pick_quality(stream, "320")

        raw_img = s.get("image", "")
        if isinstance(raw_img, list):
            raw_img = raw_img[-1].get("url", "") if raw_img else ""
        image = raw_img.replace("150x150", "500x500").replace("50x50", "500x500")

        dur_raw = (s.get("duration")
                   or s.get("more_info", {}).get("duration")
                   or 0)
        try:
            duration = float(dur_raw)
        except (ValueError, TypeError):
            duration = 0.0

        artists = (s.get("primary_artists")
                   or s.get("more_info", {}).get("primary_artists")
                   or s.get("singers")
                   or "Unknown Artist")
        if isinstance(artists, list):
            artists = ", ".join(a.get("name", "") for a in artists if a.get("name"))

        song_id = s.get("id") or s.get("songid") or s.get("song_id") or ""
        title   = s.get("song") or s.get("title") or s.get("name") or "Unknown"

        return Track(
            source="saavn",
            source_id=str(song_id),
            title=title,
            artist=str(artists),
            album=s.get("album") or "",
            duration=duration,
            image_url=image,
            stream_url=stream,
            year=str(s.get("year") or ""),
        )
    except Exception as e:
        print(f"[Saavn] parse error: {e}")
        return None


def get_stream_url(source_id: str) -> str:
    """Resolve stream URL — tries 3 strategies in order."""
    print(f"[Saavn] resolving: {source_id}")

    url = _strategy_song_details(source_id)
    if url:
        return url

    url = _strategy_webapi(source_id)
    if url:
        return url

    url = _strategy_community(source_id)
    if url:
        return url

    print(f"[Saavn] all strategies failed for: {source_id}")
    return ""


def _strategy_song_details(source_id: str) -> str:
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
        r.raise_for_status()
        data = r.json()
        song = data.get(source_id) or {}
        if not song:
            for v in data.values():
                if isinstance(v, dict):
                    song = v
                    break
        enc = song.get("encrypted_media_url", "")
        if enc:
            url = _decrypt_url(enc)
            return _pick_quality(url, "320") if url else ""
    except Exception as e:
        print(f"[Saavn] strategy1 error: {e}")
    return ""


def _strategy_webapi(source_id: str) -> str:
    try:
        params = {
            "__call": "webapi.get",
            "token": source_id,
            "type": "song",
            "_format": "json",
            "_marker": "0",
            "api_version": "4",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        songs = data.get("songs") or data.get("song") or []
        if isinstance(songs, dict):
            songs = [songs]
        for s in songs:
            enc = s.get("encrypted_media_url", "")
            if enc:
                url = _decrypt_url(enc)
                if url:
                    return _pick_quality(url, "320")
    except Exception as e:
        print(f"[Saavn] strategy2 error: {e}")
    return ""


def _strategy_community(source_id: str) -> str:
    """saavn.dev community API (no decryption needed)."""
    try:
        r = requests.get(
            f"{SAAVN_API}/songs/{source_id}",
            headers={"User-Agent": HEADERS["User-Agent"], "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        songs = data.get("data", {})
        if isinstance(songs, dict):
            songs = songs.get("songs") or [songs]
        if isinstance(songs, list) and songs:
            dl = songs[0].get("downloadUrl") or []
            if dl:
                best = sorted(dl, key=lambda x: int(x.get("quality","0").replace("kbps","")), reverse=True)
                url = best[0].get("url", "")
                if url:
                    print(f"[Saavn] community API ok")
                    return url
    except Exception as e:
        print(f"[Saavn] strategy3 error: {e}")
    return ""


def search_songs(query: str, n: int = 20, page: int = 1) -> List[Track]:
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


def get_top_charts() -> List[Track]:
    try:
        params = {
            "__call": "content.getAlbums",
            "album_id": "52253978",
            "api_version": "4",
            "_format": "json",
            "_marker": "0",
            "ctx": "web6dot0",
        }
        r = requests.get(SAAVN_BASE, params=params, headers=HEADERS, timeout=TIMEOUT)
        data = r.json()
        songs = data.get("songs") or data.get("list") or []
        tracks = [_parse_song(s) for s in songs]
        result = [t for t in tracks if t]
        return result if result else search_songs("top hindi songs 2025", n=20)
    except Exception as e:
        print(f"[Saavn] charts error: {e}")
        return search_songs("trending songs 2025", n=20)


def get_new_releases() -> List[Track]:
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
