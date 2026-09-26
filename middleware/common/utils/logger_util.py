import logging
import sys
from collections.abc import Callable
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TypeVar

_ROOT_LOGGER_NAME = "middleware"
_MAX_BYTES = 1_048_576
_BACKUP_COUNT = 5
_configured = False

F = TypeVar("F", bound=Callable)
C = TypeVar("C", bound=type)


def _log_file() -> Path:
    log_dir = Path(__file__).resolve().parents[3] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "middleware.log"


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    rolling_file = RotatingFileHandler(
        _log_file(),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    rolling_file.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(rolling_file)
    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    configure_logging()
    if name is None or name == _ROOT_LOGGER_NAME:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    if name.startswith(f"{_ROOT_LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def log_call(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info("ENTER %s", func.__qualname__)
        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception("EXIT %s", func.__qualname__)
            raise
        logger.info("EXIT %s", func.__qualname__)
        return result

    return wrapper  # type: ignore[return-value]


def log_methods(cls: C) -> C:
    for name, attr in list(cls.__dict__.items()):
        if name.startswith("__"):
            continue
        if isinstance(attr, staticmethod):
            setattr(cls, name, staticmethod(log_call(attr.__func__)))
        elif isinstance(attr, classmethod):
            setattr(cls, name, classmethod(log_call(attr.__func__)))
        elif isinstance(attr, property):
            continue
        elif callable(attr):
            setattr(cls, name, log_call(attr))
    return cls
