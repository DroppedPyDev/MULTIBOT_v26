import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Copy .env.example to .env and fill it in "
        "(or set it in your platform's environment variables)."
    )

MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
TEMP_DIR = os.getenv("TEMP_DIR", "temp")

# Telegram bot API upload limit for regular bots
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# --- AI Assistant ---
# Get a key at https://console.anthropic.com/ — AI features are disabled
# (with a friendly message) if this isn't set, everything else still works.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-5")
MAX_AI_HISTORY = int(os.getenv("MAX_AI_HISTORY", "10"))

# --- Cloud Storage ---
# A private Telegram channel the bot is an admin of; files are stored there
# and referenced back to users. See README for how to get this ID.
_storage_channel_raw = os.getenv("CLOUD_STORAGE_CHANNEL_ID")
CLOUD_STORAGE_CHANNEL_ID = int(_storage_channel_raw) if _storage_channel_raw else None

# --- Developer info page ---
DEVELOPER_NAME = os.getenv("DEVELOPER_NAME", "Your Name Here")
DEVELOPER_USERNAME = os.getenv("DEVELOPER_USERNAME", "your_username")
DEVELOPER_GITHUB = os.getenv("DEVELOPER_GITHUB", "")
