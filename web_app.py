"""
Lily Music Player — Web Application (FastAPI)
Deploy: uvicorn web_app:app --host 0.0.0.0 --port $PORT
"""
import os, sys, re
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel
import uvicorn

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR",  "/tmp/lily_uploads"))
DB_PATH    = Path(os.getenv("DB_PATH",     str(Path.home() / ".lily" / "lily.db")))
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Lily Music Player", version="2.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

from core.database import Database
from core.models import Track
from core.metadata import read_metadata, AUDIO_EXTENSIONS

db = Database(DB_PATH)

# ── Keep-alive (prevents Render free tier spin-down) ─────────────────────────
import threading, time, urllib.request

def _self_ping():
    """Ping ourselves every 10 minutes so Render doesn't spin us down."""
    time.sleep(60)  # Wait 1 min after startup before first ping
    url = os.getenv("RENDER_EXTERNAL_URL", "")
    if not url:
        # Try to detect from environment
        svc = os.getenv("RENDER_SERVICE_NAME", "")
        if svc:
            url = f"https://{svc}.onrender.com"
    if not url:
        print("[KeepAlive] No URL found, skipping pings")
        return
    ping_url = url.rstrip("/") + "/api/ping"
    print(f"[KeepAlive] Will ping {ping_url} every 10 minutes")
    while True:
        try:
            urllib.request.urlopen(ping_url, timeout=10)
            print(f"[KeepAlive] Pinged OK at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[KeepAlive] Ping failed: {e}")
        time.sleep(600)  # 10 minutes

_ping_thread = threading.Thread(target=_self_ping, daemon=True)
_ping_thread.start()



# ── Simple in-memory stream URL cache (avoids repeat API calls) ──────────────
_stream_cache: dict = {}   # source_id -> url

# ── Helpers ─────────────────────────────────────────────────────────────────
MIME = {
    ".mp3": "audio/mpeg", ".flac": "audio/flac",
    ".ogg": "audio/ogg",  ".opus": "audio/ogg",
    ".m4a": "audio/mp4",  ".aac": "audio/aac",
    ".wav": "audio/wav",  ".wma": "audio/x-ms-wma",
}

def audio_mime(path: str) -> str:
    return MIME.get(Path(path).suffix.lower(), "audio/mpeg")

def parse_range(header: str, size: int):
    m = re.match(r"bytes=(\d*)-(\d*)", header or "")
    if not m:
        return 0, size - 1
    start = int(m.group(1)) if m.group(1) else 0
    end   = int(m.group(2)) if m.group(2) else size - 1
    return start, min(end, size - 1)

# ── Tracks ──────────────────────────────────────────────────────────────────

@app.get("/api/tracks")
def list_tracks(search: Optional[str] = None, sort: str = "artist"):
    return [t.to_dict() for t in db.get_all_local_tracks(search=search, sort=sort)]

@app.post("/api/tracks/upload")
async def upload_tracks(files: List[UploadFile] = File(...)):
    added, errors = [], []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            errors.append(f"{f.filename}: unsupported format"); continue
        try:
            dest = UPLOAD_DIR / f.filename
            n = 1
            while dest.exists():
                dest = UPLOAD_DIR / f"{Path(f.filename).stem}_{n}{ext}"; n += 1
            dest.write_bytes(await f.read())
            track = read_metadata(str(dest))
            tid   = db.upsert_local_track(track)
            track.id = tid
            d = track.to_dict(); d["id"] = tid
            added.append(d)
        except Exception as e:
            errors.append(f"{f.filename}: {e}")
    return {"added": len(added), "tracks": added, "errors": errors}

@app.delete("/api/tracks/{track_id}")
def delete_track(track_id: int):
    t = db.get_local_track(track_id)
    if t and t.file_path and os.path.exists(t.file_path):
        try: os.remove(t.file_path)
        except: pass
    db.delete_local_track(track_id)
    return {"ok": True}

@app.get("/api/stream/{track_id}")
async def stream_track(track_id: int, request: Request):
    t = db.get_local_track(track_id)
    if not t: raise HTTPException(404, "Track not found")
    if not os.path.exists(t.file_path): raise HTTPException(404, "File missing")

    db.increment_play_count(track_id)
    size = os.path.getsize(t.file_path)
    mime = audio_mime(t.file_path)
    rng  = request.headers.get("range")

    if rng:
        start, end  = parse_range(rng, size)
        chunk_size  = end - start + 1
        def gen():
            with open(t.file_path, "rb") as fh:
                fh.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    data = fh.read(min(65536, remaining))
                    if not data: break
                    remaining -= len(data)
                    yield data
        return StreamingResponse(gen(), 206, media_type=mime, headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        })

    return StreamingResponse(open(t.file_path, "rb"), media_type=mime, headers={
        "Content-Length": str(size), "Accept-Ranges": "bytes",
    })

@app.get("/api/artwork/{track_id}")
def get_artwork(track_id: int):
    t = db.get_local_track(track_id)
    if not t or not t.file_path or not os.path.exists(t.file_path):
        raise HTTPException(404)
    try:
        meta = read_metadata(t.file_path)
        if meta.artwork_data:
            return Response(meta.artwork_data, media_type="image/jpeg")
    except: pass
    raise HTTPException(404, "No artwork")

# ── Playlists ────────────────────────────────────────────────────────────────

class PlaylistBody(BaseModel):
    name: str

class AddTrackBody(BaseModel):
    track_id: int

@app.get("/api/playlists")
def list_playlists():
    return [{"id": p.id, "name": p.name, "track_count": p.track_count}
            for p in db.get_playlists()]

@app.post("/api/playlists")
def create_playlist(body: PlaylistBody):
    pid = db.create_playlist(body.name)
    return {"id": pid, "name": body.name, "track_count": 0}

@app.put("/api/playlists/{pid}")
def rename_playlist(pid: int, body: PlaylistBody):
    db.rename_playlist(pid, body.name); return {"ok": True}

@app.delete("/api/playlists/{pid}")
def delete_playlist(pid: int):
    db.delete_playlist(pid); return {"ok": True}

@app.get("/api/playlists/{pid}/tracks")
def playlist_tracks(pid: int):
    return [t.to_dict() for t in db.get_playlist_tracks(pid)]

@app.post("/api/playlists/{pid}/tracks")
def add_to_playlist(pid: int, body: AddTrackBody):
    t = db.get_local_track(body.track_id)
    if not t: raise HTTPException(404)
    db.add_track_to_playlist(pid, t)
    return {"ok": True}

@app.delete("/api/playlists/{pid}/tracks/{position}")
def remove_from_playlist(pid: int, position: int):
    db.remove_from_playlist(pid, position); return {"ok": True}

# ── Search ───────────────────────────────────────────────────────────────────

@app.get("/api/search/saavn")
def search_saavn(q: str = Query(..., min_length=1)):
    try:
        from services.saavn import search_songs
        tracks = search_songs(q, n=25)
        result = []
        for t in tracks:
            d = t.to_dict()
            # Cache stream URLs from search results immediately
            if t.stream_url and t.source_id:
                _stream_cache[t.source_id] = t.stream_url
            result.append(d)
        return result
    except Exception as e:
        print(f"[Saavn search] {e}"); return []

@app.get("/api/search/youtube")
def search_youtube(q: str = Query(..., min_length=1)):
    try:
        from services.youtube import search_songs
        return [t.to_dict() for t in search_songs(q, n=15)]
    except Exception as e:
        print(f"[YouTube] {e}"); return []

# ── Stream URL resolution ─────────────────────────────────────────────────────

@app.get("/api/resolve/saavn/{source_id}")
def resolve_saavn(source_id: str, stream_url: str = Query(default="")):
    """
    Resolve JioSaavn stream URL.
    If the frontend already has stream_url (from search results), accept it directly.
    Otherwise hit the API.
    """
    # 1. Frontend passed a pre-resolved URL (from search)
    if stream_url:
        _stream_cache[source_id] = stream_url
        return {"url": stream_url}

    # 2. Check cache
    if source_id in _stream_cache:
        return {"url": _stream_cache[source_id]}

    # 3. Fetch from API
    try:
        from services.saavn import get_stream_url
        url = get_stream_url(source_id)
        if url:
            _stream_cache[source_id] = url
            return {"url": url}
    except Exception as e:
        raise HTTPException(500, str(e))

    raise HTTPException(404, "Could not resolve JioSaavn stream URL. "
                        "Ensure pycryptodome is installed: pip install pycryptodome")

@app.get("/api/resolve/youtube/{video_id}")
def resolve_youtube(video_id: str):
    if video_id in _stream_cache:
        return {"url": _stream_cache[video_id]}
    try:
        from services.youtube import get_stream_url
        url = get_stream_url(video_id)
        if url:
            _stream_cache[video_id] = url
            return {"url": url}
    except Exception as e:
        raise HTTPException(500, str(e))
    raise HTTPException(404, "No YouTube stream URL found")

# ── Lyrics ───────────────────────────────────────────────────────────────────

@app.get("/api/lyrics")
def lyrics_api(title: str, artist: str = "", album: str = "", duration: float = 0):
    try:
        from services.lyrics import get_lyrics
        lyr = get_lyrics(title, artist, album, duration)
        if lyr and lyr.has_any:
            return {
                "has_synced": lyr.has_synced, "has_plain": lyr.has_plain,
                "synced": [{"time_ms": l.time_ms, "text": l.text} for l in lyr.synced],
                "plain": lyr.plain, "source": "lrclib.net",
            }
    except Exception as e:
        print(f"[Lyrics] {e}")
    return {"has_synced": False, "has_plain": False, "synced": [], "plain": "", "source": ""}

# ── Home ─────────────────────────────────────────────────────────────────────

@app.get("/api/charts")
def charts():
    try:
        from services.saavn import get_top_charts
        tracks = get_top_charts()[:20]
        for t in tracks:
            if t.stream_url and t.source_id:
                _stream_cache[t.source_id] = t.stream_url
        return [t.to_dict() for t in tracks]
    except: return []

@app.get("/api/releases")
def new_releases():
    try:
        from services.saavn import get_new_releases
        tracks = get_new_releases()[:20]
        for t in tracks:
            if t.stream_url and t.source_id:
                _stream_cache[t.source_id] = t.stream_url
        return [t.to_dict() for t in tracks]
    except: return []

# ── Ping / Health ────────────────────────────────────────────────────────────
import datetime

@app.get("/api/ping")
def ping():
    return {"status": "alive", "time": datetime.datetime.utcnow().isoformat(), "service": "Lily Music"}

# ── SPA ──────────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
@app.get("/{full_path:path}")
def serve_spa(full_path: str = ""):
    idx = STATIC_DIR / "index.html"
    if idx.exists(): return FileResponse(str(idx))
    return {"status": "Lily API running", "docs": "/docs"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("web_app:app", host="0.0.0.0", port=port, reload=False)
