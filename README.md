# Telegram File Downloader & Media Converter Bot

First module of a larger multi-feature Telegram bot project. This module handles:
- Downloading media from URLs (YouTube and other `yt-dlp`-supported sites)
- Converting sent media between formats (e.g. video → mp3, video → gif)

Built with **Python 3.11** + **aiogram 3** (async). Runs as a single long-lived
process (polling mode) so it deploys cleanly on Railway, Render, or Fly.io
using the included `Dockerfile`.

## Project layout

```
telegram-bot/
├── Dockerfile
├── requirements.txt
├── .env.example
├── railway.json         # Railway config (auto-detects Dockerfile too)
├── render.yaml           # Render "background worker" config
├── fly.toml               # Fly.io config
└── bot/
    ├── main.py            # entrypoint — starts the bot
    ├── config.py          # loads env vars
    ├── handlers/
    │   ├── start.py       # /start, /help
    │   └── download.py    # /download <url>, and file-conversion flow
    ├── services/
    │   ├── downloader.py  # yt-dlp wrapper
    │   └── converter.py   # ffmpeg wrapper
    └── utils/
        └── cleanup.py     # temp file management
```

## Local setup

```bash
cp .env.example .env        # then fill in BOT_TOKEN
pip install -r requirements.txt
python -m bot.main
```

You'll also need `ffmpeg` installed locally (the Dockerfile installs it
automatically for deployment):

```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

## Deploying

### Railway
1. Push this repo to GitHub.
2. On [railway.app](https://railway.app), "New Project" → "Deploy from GitHub repo".
3. Railway auto-detects the `Dockerfile`. Add the `BOT_TOKEN` environment
   variable in the Railway dashboard (Variables tab).
4. Deploy — no port/domain needed since this is a polling worker, not a web server.

### Render
1. Push to GitHub.
2. "New" → "Background Worker" → connect the repo. Render will read `render.yaml`.
3. Add `BOT_TOKEN` under Environment.

### Fly.io
1. Install `flyctl`, run `fly launch` in this directory (it will detect `fly.toml`/Dockerfile).
2. `fly secrets set BOT_TOKEN=your_token_here`
3. `fly deploy`

## Getting a bot token

Message [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`,
follow the prompts, and copy the token it gives you into `BOT_TOKEN`.

## What's implemented so far

- `/start`, `/help`
- `/download <url>` — downloads media via `yt-dlp` and sends it back
  (auto-picks best quality under Telegram's 50MB bot upload limit)
- Send a video/audio file directly → bot offers inline buttons to convert it
  (e.g. extract audio as MP3, convert video to GIF)
- Concurrency capped (default 3 simultaneous jobs) so heavy conversions don't
  block other users; temp files are deleted after sending

## Next modules (not yet built)
- Group Management & Moderation
- AI Assistant/Chatbot
- Cloud Storage & Organization
