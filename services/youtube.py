"""
YouTube streaming service using yt-dlp.
"""

from typing import List, Optional
from core.models import Track


def _ydl_opts(quiet: bool = True) -> dict:
    return {
        "format": "bestaudio/best",
        "quiet": quiet,
        "no_warnings": quiet,
        "extract_flat": False,
        "noplaylist": True,
        "youtube_include_dash_manifest": False,
    }


def search_songs(query: str, n: int = 15) -> List[Track]:
    try:
        import yt_dlp
        opts = {**_ydl_opts(), "extract_flat": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
            entries = info.get("entries") or []
            tracks = []
            for e in entries:
                if not e:
                    continue
                dur = e.get("duration") or 0
                if dur > 600:
                    continue
                thumb = ""
                thumbs = e.get("thumbnails") or []
                if thumbs:
                    thumb = thumbs[-1].get("url", "")
                tracks.append(Track(
                    source="youtube",
                    source_id=e.get("id") or "",
                    title=e.get("title") or "Unknown",
                    artist=e.get("uploader") or e.get("channel") or "Unknown Artist",
                    album="YouTube",
                    duration=float(dur),
                    image_url=thumb,
                ))
            return tracks
    except ImportError:
        print("[YouTube] yt-dlp not installed")
        return []
    except Exception as e:
        print(f"[YouTube] search error: {e}")
        return []


def get_stream_url(video_id: str) -> str:
    try:
        import yt_dlp
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats") or []
            audio_formats = [f for f in formats if
                             f.get("acodec") != "none" and f.get("vcodec") == "none"]
            if audio_formats:
                audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)
                return audio_formats[0].get("url") or info.get("url") or ""
            return info.get("url") or ""
    except ImportError:
        print("[YouTube] yt-dlp not installed")
        return ""
    except Exception as e:
        print(f"[YouTube] stream url error: {e}")
        return ""
