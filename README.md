# 🌸 Bloomee — Python/PyQt6 Full Replica

A feature-complete Python replica of the Bloomee music player, with live song streaming from **JioSaavn** and **YouTube**, local library management, playlists, and a polished dark UI.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install PyQt6 yt-dlp requests pycryptodome mutagen Pillow

# 2. Run
python main.py
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎵 **JioSaavn Streaming** | Search & stream millions of songs via JioSaavn's unofficial API |
| ▶ **YouTube Streaming** | Search and stream audio from YouTube via yt-dlp |
| 📚 **Local Library** | Add local MP3/FLAC/OGG/M4A/WAV files with full metadata |
| 🗂️ **Playlists** | Create, rename, delete playlists; add any track from any source |
| 🏠 **Home Page** | Live trending charts and new releases from JioSaavn |
| 🔍 **Search** | Simultaneous search across JioSaavn + YouTube |
| 🎨 **Album Artwork** | Embedded artwork (local) and thumbnail images (streaming) |
| 🔀 **Shuffle & Repeat** | Full playback mode controls |
| ≡ **Queue** | View and manage the current play queue |
| 📖 **History** | Listening history stored in SQLite |
| 📂 **Drag & Drop** | Drop audio files or folders directly onto the window |
| ⌨️ **Keyboard Shortcuts** | Space, Ctrl+←/→, Ctrl+F, Ctrl+L |

---

## 📁 Project Structure

```
bloomee/
├── main.py                  ← Entry point
├── requirements.txt
├── core/
│   ├── database.py          ← SQLite persistence (tracks, playlists, history)
│   ├── models.py            ← Track and Playlist data classes
│   ├── metadata.py          ← Local audio file metadata reader (mutagen)
│   └── player.py            ← PyQt6 QMediaPlayer wrapper (local + streaming)
├── services/
│   ├── saavn.py             ← JioSaavn unofficial API (search, charts, stream URLs)
│   └── youtube.py           ← YouTube streaming via yt-dlp
└── ui/
    ├── styles.py            ← Global dark theme stylesheet
    ├── widgets.py           ← Shared reusable widgets (ArtworkLabel, TrackCard, etc.)
    ├── player_bar.py        ← Bottom playback controls
    ├── sidebar.py           ← Left navigation sidebar
    ├── track_table.py       ← Reusable track list table
    ├── main_window.py       ← Root window, wires everything together
    └── pages/
        ├── home_page.py     ← Live trending + new releases
        ├── search_page.py   ← JioSaavn + YouTube search
        ├── library_page.py  ← Local music library
        ├── playlist_page.py ← Playlist tracks view
        └── queue_page.py    ← Current play queue
```

---

## 🎛️ How Online Streaming Works

### JioSaavn
1. Search via JioSaavn's public API (`jiosaavn.com/api.php`)
2. Results include an `encrypted_media_url` field
3. The URL is DES-encrypted with key `"38346591"` (ECB mode)
4. After decryption, the URL is upgraded to 320kbps quality
5. PyQt6 QMediaPlayer streams the direct audio URL

### YouTube
1. Search via `yt-dlp` (`ytsearch15:query`)
2. Filter results to audio-only formats
3. `yt-dlp` extracts the direct audio stream URL
4. PyQt6 QMediaPlayer streams it directly

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Play / Pause |
| `Ctrl + →` | Next track |
| `Ctrl + ←` | Previous track |
| `Ctrl + F` | Focus search |
| `Ctrl + L` | Go to Library |

---

## 🔧 Troubleshooting

**No audio plays:**
- Make sure PyQt6 multimedia is available: `pip install PyQt6`
- On Linux, install: `sudo apt install python3-pyqt6.qtmultimedia libqt6multimedia6`

**JioSaavn streams fail:**
- Ensure `pycryptodome` is installed: `pip install pycryptodome`
- Note: Some songs may be region-restricted

**YouTube streams fail:**
- Update yt-dlp: `pip install -U yt-dlp`
- YouTube changes their API frequently; yt-dlp handles this automatically

**Album art not showing:**
- Install Pillow: `pip install Pillow`

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `PyQt6` | UI framework + audio playback |
| `yt-dlp` | YouTube stream URL extraction |
| `requests` | HTTP calls to JioSaavn API |
| `pycryptodome` | DES decryption for JioSaavn media URLs |
| `mutagen` | Audio file metadata reading |
| `Pillow` | Album art image processing |
