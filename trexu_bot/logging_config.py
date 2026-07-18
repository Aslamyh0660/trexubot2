import logging
from logging.handlers import RotatingFileHandler

from .constants import LOG_DIR


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        return

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_DIR / 'trexu_bot.log', maxBytes=2_000_000, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
