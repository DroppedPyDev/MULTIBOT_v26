import asyncio
import os
import uuid
import logging
from dataclasses import dataclass

import yt_dlp

from bot.config import TEMP_DIR, MAX_UPLOAD_BYTES

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    file_path: str
    title: str
    is_audio: bool


class DownloadError(Exception):
    pass


def _run_download(url: str, out_template: str) -> dict:
    """Blocking yt-dlp call — run this inside a thread/executor."""
    ydl_opts = {
        "outtmpl": out_template,
        "format": f"best[filesize<{MAX_UPLOAD_BYTES}]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info


async def download_media(url: str) -> DownloadResult:
    """Download media from a URL via yt-dlp. Runs the blocking call in a thread
    so it doesn't block the bot's event loop."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    job_id = uuid.uuid4().hex[:8]
    out_template = os.path.join(TEMP_DIR, f"{job_id}.%(ext)s")

    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, _run_download, url, out_template)
    except yt_dlp.utils.DownloadError as e:
        raise DownloadError(str(e)) from e

    # yt-dlp fills in the real extension after download
    ext = info.get("ext", "mp4")
    file_path = os.path.join(TEMP_DIR, f"{job_id}.{ext}")
    if not os.path.exists(file_path):
        # some extractors post-process to a different final file; fall back to
        # scanning for the job_id
        for fname in os.listdir(TEMP_DIR):
            if fname.startswith(job_id):
                file_path = os.path.join(TEMP_DIR, fname)
                break
        else:
            raise DownloadError("Download finished but the output file was not found.")

    size = os.path.getsize(file_path)
    if size > MAX_UPLOAD_BYTES:
        os.remove(file_path)
        raise DownloadError(
            "The file is too large for Telegram's 50MB bot upload limit."
        )

    return DownloadResult(
        file_path=file_path,
        title=info.get("title", "download"),
        is_audio=info.get("vcodec") == "none",
    )
