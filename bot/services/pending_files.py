import uuid
from dataclasses import dataclass


@dataclass
class PendingFile:
    file_id: str
    file_type: str  # "video" | "audio" | "document"
    filename: str
    size_bytes: int | None


# Telegram callback_data is capped at 64 bytes, and file_id strings routinely
# exceed that — so buttons reference a short id here instead of the raw file_id.
_pending: dict[str, PendingFile] = {}


def register(file_id: str, file_type: str, filename: str, size_bytes: int | None) -> str:
    ref = uuid.uuid4().hex[:10]
    _pending[ref] = PendingFile(file_id, file_type, filename, size_bytes)
    return ref


def get(ref: str) -> PendingFile | None:
    return _pending.get(ref)


def pop(ref: str) -> PendingFile | None:
    return _pending.pop(ref, None)
