"""Simple structured logging for ETL modules."""

from __future__ import annotations

import logging
import sys

from lib.settings import settings

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger. Call once per module: `log = get_logger(__name__)`."""
    global _configured
    if not _configured:
        logging.basicConfig(
            level=settings.log_level,
            format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stdout,
        )
        _configured = True
    return logging.getLogger(name)
