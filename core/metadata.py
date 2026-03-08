"""Local audio file metadata extraction."""
from pathlib import Path
from typing import Optional
from core.models import Track

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".mp4", ".aac", ".wav", ".wma"}


def read_metadata(filepath: str) -> Track:
    """Read audio metadata from a local file."""
    path = Path(filepath)
    track = Track(
        source="local",
        file_path=filepath,
        title=path.stem,
        artist="Unknown Artist",
        album="Unknown Album",
    )
    try:
        from mutagen import File as MFile
        audio = MFile(filepath)
        if audio is None:
            return track
        if hasattr(audio, "info") and hasattr(audio.info, "length"):
            track.duration = audio.info.length
        tags = audio.tags
        if tags is None:
            return track
        ext = path.suffix.lower()
        if ext == ".mp3":
            track.title  = _id3(tags, "TIT2") or track.title
            track.artist = _id3(tags, "TPE1") or track.artist
            track.album  = _id3(tags, "TALB") or track.album
            track.year   = _id3(tags, "TDRC") or _id3(tags, "TYER") or ""
            track.genre  = _id3(tags, "TCON") or ""
            for k, v in tags.items():
                if k.startswith("APIC"):
                    track.artwork_data = v.data
                    break
        elif ext in (".flac", ".ogg", ".opus"):
            track.title  = _vorbis(tags, "title")  or track.title
            track.artist = _vorbis(tags, "artist") or track.artist
            track.album  = _vorbis(tags, "album")  or track.album
            track.year   = _vorbis(tags, "date")   or _vorbis(tags, "year") or ""
            track.genre  = _vorbis(tags, "genre")  or ""
            try:
                pics = audio.pictures
                if pics:
                    track.artwork_data = pics[0].data
            except Exception:
                pass
        elif ext in (".m4a", ".aac", ".mp4"):
            track.title  = _m4a(tags, "©nam") or track.title
            track.artist = _m4a(tags, "©ART") or track.artist
            track.album  = _m4a(tags, "©alb") or track.album
            track.year   = _m4a(tags, "©day") or ""
            track.genre  = _m4a(tags, "©gen") or ""
            covr = tags.get("covr")
            if covr:
                track.artwork_data = bytes(covr[0])
    except ImportError:
        pass
    except Exception as e:
        print(f"[Metadata] error reading {filepath}: {e}")
    return track


def _id3(tags, key: str) -> Optional[str]:
    v = tags.get(key)
    return str(v[0]) if v else None


def _vorbis(tags, key: str) -> Optional[str]:
    v = tags.get(key.lower()) or tags.get(key.upper())
    return v[0] if v else None


def _m4a(tags, key: str) -> Optional[str]:
    v = tags.get(key)
    return str(v[0]) if v else None


def scan_directory(directory: str):
    """Yield audio file paths in a directory recursively."""
    import os
    for root, _, files in os.walk(directory):
        for f in files:
            if Path(f).suffix.lower() in AUDIO_EXTENSIONS:
                yield os.path.join(root, f)
