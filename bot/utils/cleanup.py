import os
import logging

logger = logging.getLogger(__name__)


def safe_delete(*paths: str) -> None:
    """Delete temp files, ignoring any that are already gone."""
    for path in paths:
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            logger.warning(f"Could not delete temp file {path}: {e}")
