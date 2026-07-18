from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

URL_RE = re.compile(r'https?://[^\s]+', re.IGNORECASE)


def is_url(text: str) -> bool:
    return bool(URL_RE.search(text or ''))


def sanitize_filename(name: str, max_len: int = 120) -> str:
    cleaned = re.sub(r'[^\w\-.() \u0600-\u06FF]+', '_', name, flags=re.UNICODE).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return (cleaned or 'file')[:max_len]


def extract_platform(url: str, extractor: str | None = None) -> str:
    if extractor:
        return extractor.split(':', 1)[0].lower()
    host = urlparse(url).netloc.lower()
    for value in ('youtube', 'youtu', 'instagram', 'twitter', 'x.com', 'tiktok', 'facebook', 'soundcloud', 'pinterest', 'reddit', 'dailymotion'):
        if value in host:
            return value.replace('x.com', 'twitter')
    return host or 'direct'


def format_duration(seconds: int | float | None) -> str:
    if not seconds:
        return '00:00'
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    return f'{minutes:02d}:{secs:02d}'


def progress_bar(percent: float, width: int = 12) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int((percent / 100) * width)
    return '█' * filled + '░' * (width - filled)


def utcnow() -> datetime:
    return datetime.utcnow()


def make_token(size: int = 8) -> str:
    return secrets.token_hex(size // 2 if size % 2 == 0 else size)


def human_size(size_bytes: int | None) -> str:
    if not size_bytes:
        return '-'
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024 or unit == 'TB':
            return f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
