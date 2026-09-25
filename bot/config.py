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
