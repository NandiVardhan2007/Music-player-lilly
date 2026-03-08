# 🌸 Lily Music Player — Web Edition

A full-featured music player web app converted from the PyQt6 desktop app.
Streams local files, JioSaavn, and YouTube audio directly in the browser.

## Features
- 🎵 Upload & play local music (MP3, FLAC, OGG, M4A, WAV, OPUS)
- 🌐 Stream from JioSaavn & YouTube
- 📝 Synced lyrics via lrclib.net
- 🗂 Playlists, queue, library management
- 🎨 Beautiful dark UI with animated lyrics
- 📦 SQLite database, no external DB needed

---

## 🚀 Deploy on Render

### 1. Push your project to GitHub
Make sure the repo contains:
```
web_app.py
render.yaml
requirements-web.txt
Procfile
static/index.html
core/
services/
```

### 2. Create a new Web Service on render.com
- Connect your GitHub repo
- Render auto-detects `render.yaml` — just click **Deploy**

### 3. Environment Variables (auto-set by render.yaml)
| Variable | Value |
|----------|-------|
| `UPLOAD_DIR` | `/tmp/lily_uploads` |
| `DB_PATH` | `/tmp/lily_music/lily.db` |

> ⚠️ **Note**: Render free tier has an ephemeral filesystem.
> Uploaded files and the database are lost on restart.
> For persistence, add a [Render Disk](https://render.com/docs/disks)
> and set `UPLOAD_DIR` / `DB_PATH` to the disk mount path.

---

## 🖥 Run Locally

```bash
# Install dependencies
pip install -r requirements-web.txt

# Start the server
uvicorn web_app:app --host 0.0.0.0 --port 8000 --reload

# Open browser
open http://localhost:8000
```

---

## 📁 File Structure
```
web_app.py          ← FastAPI backend (all API routes)
static/index.html   ← React SPA (the full UI)
core/
  database.py       ← SQLite persistence layer
  models.py         ← Track / Playlist data models
  metadata.py       ← Audio file metadata reader
  player.py         ← (desktop only, not used in web)
services/
  saavn.py          ← JioSaavn streaming service
  youtube.py        ← YouTube streaming via yt-dlp
  lyrics.py         ← Synced lyrics via lrclib.net
requirements-web.txt
Procfile
render.yaml
```

## API Reference
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tracks` | List library tracks |
| POST | `/api/tracks/upload` | Upload audio files |
| GET | `/api/stream/{id}` | Stream a local track |
| GET | `/api/artwork/{id}` | Get embedded artwork |
| GET/POST | `/api/playlists` | List / create playlists |
| GET | `/api/search/saavn?q=` | Search JioSaavn |
| GET | `/api/search/youtube?q=` | Search YouTube |
| GET | `/api/resolve/saavn/{id}` | Get Saavn stream URL |
| GET | `/api/resolve/youtube/{id}` | Get YouTube stream URL |
| GET | `/api/lyrics?title=&artist=` | Fetch lyrics |
| GET | `/api/charts` | JioSaavn trending |
