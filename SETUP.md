# Lily Music Player — Setup Guide

## Required folder structure

```
lily/                          ← project root
├── main.py
├── core/
│   ├── __init__.py
│   ├── database.py
│   ├── metadata.py
│   ├── models.py
│   └── player.py
├── services/
│   ├── __init__.py
│   ├── lyrics.py
│   ├── saavn.py
│   └── youtube.py
└── ui/
    ├── __init__.py
    ├── main_window.py
    ├── player_bar.py
    ├── sidebar.py
    ├── styles.py
    ├── widgets.py
    └── pages/
        ├── __init__.py
        ├── home_page.py      ← NEW
        ├── library_page.py   ← NEW
        ├── lyrics_page.py    ← NEW
        ├── playlist_page.py  ← NEW
        ├── queue_page.py     ← NEW
        └── search_page.py    ← NEW
```

## Install dependencies

```bash
pip install PyQt6 requests mutagen Pillow pycryptodome yt-dlp
```

### On Linux — also install GStreamer (required for PyQt6 audio):
```bash
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav
```

### On Windows:
PyQt6 on Windows uses DirectShow/Media Foundation — no extra codecs needed.

## Run
```bash
cd lily
python main.py
```

## What each dependency does

| Package        | Purpose                                          |
|----------------|--------------------------------------------------|
| PyQt6          | UI framework + audio playback                    |
| requests       | HTTP calls to JioSaavn and lrclib.net            |
| mutagen        | Read audio file metadata (ID3, FLAC, M4A, etc.)  |
| Pillow         | Resize artwork images                            |
| pycryptodome   | Decrypt JioSaavn stream URLs (DES)               |
| yt-dlp         | Search YouTube and extract audio stream URLs     |

> **Note:** Without `pycryptodome`, JioSaavn tracks will have no stream URL.
> Without `yt-dlp`, YouTube search is disabled. Local file playback always works.
