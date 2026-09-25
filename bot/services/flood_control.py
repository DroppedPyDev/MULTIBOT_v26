import time
from collections import defaultdict, deque

# Per (chat_id, user_id) -> deque of recent message timestamps.
# In-memory is fine here: flood detection only needs a short rolling window,
# losing it on restart has no real consequence.
_message_log: dict[tuple[int, int], deque] = defaultdict(lambda: deque(maxlen=50))


def record_message(chat_id: int, user_id: int) -> None:
    _message_log[(chat_id, user_id)].append(time.monotonic())


def is_flooding(chat_id: int, user_id: int, limit: int, window_seconds: int) -> bool:
    """True if the user has sent >= limit messages within window_seconds."""
    now = time.monotonic()
    timestamps = _message_log[(chat_id, user_id)]
    recent = [t for t in timestamps if now - t <= window_seconds]
    return len(recent) >= limit
