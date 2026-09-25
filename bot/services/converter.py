import asyncio
import os
import uuid
import logging

from bot.config import TEMP_DIR

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    pass


async def _run_ffmpeg(args: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise ConversionError(stderr.decode(errors="ignore")[-500:])


async def to_mp3(input_path: str) -> str:
    """Extract audio from a video/audio file as MP3."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex[:8]}.mp3")
    await _run_ffmpeg([
        "-y", "-i", input_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        output_path,
    ])
    return output_path


async def to_gif(input_path: str, duration_seconds: int = 6) -> str:
    """Convert the first N seconds of a video to a GIF."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex[:8]}.gif")
    await _run_ffmpeg([
        "-y", "-t", str(duration_seconds), "-i", input_path,
        "-vf", "fps=12,scale=480:-1:flags=lanczos",
        output_path,
    ])
    return output_path


async def to_mp4(input_path: str) -> str:
    """Re-encode/convert an arbitrary video file to MP4 (H.264/AAC)."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex[:8]}.mp4")
    await _run_ffmpeg([
        "-y", "-i", input_path,
        "-c:v", "libx264", "-c:a", "aac",
        output_path,
    ])
    return output_path
