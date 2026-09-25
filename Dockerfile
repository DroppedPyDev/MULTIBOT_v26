FROM python:3.11-slim

# ffmpeg is required for media conversion; git is required by some yt-dlp extractors
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/

# Temp dir for downloads/conversions — not persisted across deploys, which is fine,
# since files are deleted right after being sent to the user.
RUN mkdir -p /app/temp

CMD ["python", "-m", "bot.main"]
