"""Centralized logging for Athena-SDA.

Replaces ad-hoc `print()` in the pipeline with the stdlib `logging` module so
cron runs and operators get leveled, timestamped, auditable output. Idempotent:
callers can invoke `setup_logging()` from any entrypoint without clobbering an
already-configured handler.
"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once (no-op on subsequent calls)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger, ensuring the root logger is configured first."""
    setup_logging()
    return logging.getLogger(name)
