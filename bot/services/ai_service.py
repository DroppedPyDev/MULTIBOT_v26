from anthropic import AsyncAnthropic

from bot.config import ANTHROPIC_API_KEY, AI_MODEL

_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


class AIError(Exception):
    pass


def is_configured() -> bool:
    return _client is not None


async def get_reply(history: list[dict]) -> str:
    """history: list of {"role": "user"|"assistant", "content": str}, oldest first."""
    if _client is None:
        raise AIError(
            "The AI assistant isn't configured yet — the bot owner needs to set "
            "ANTHROPIC_API_KEY."
        )
    try:
        response = await _client.messages.create(
            model=AI_MODEL,
            max_tokens=1024,
            messages=history,
        )
    except Exception as e:
        raise AIError(f"AI request failed: {e}") from e

    return "".join(block.text for block in response.content if block.type == "text").strip()
