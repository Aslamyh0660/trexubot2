from __future__ import annotations

import shutil
from pathlib import Path

from ..config import Settings
from ..db import DatabaseManager


def build_startup_report(settings: Settings, db: DatabaseManager, queue_stats: dict[str, int]) -> str:
    ffmpeg_ok = bool(shutil.which('ffmpeg'))
    yt_dlp_cookie = 'configured' if settings.yt_dlp_cookie_file else 'not set'
    proxy = 'configured' if settings.proxy_url else 'not set'
    sponsor_count = len(db.list_sponsors(active_only=True))
    ffmpeg_state = 'OK' if ffmpeg_ok else 'MISSING'
    audd_state = 'set' if settings.audd_api_token else 'missing'
    genius_state = 'set' if settings.genius_api_token else 'missing'

    return (
        '🚀 Trexu Bot startup report\n\n'
        f'• ffmpeg: {ffmpeg_state}\n'
        f'• DB: {settings.database_url}\n'
        f'• Download dir: {Path(settings.download_dir).as_posix()}\n'
        f'• Temp dir: {Path(settings.temp_dir).as_posix()}\n'
        f'• AudD token: {audd_state}\n'
        f'• Genius token: {genius_state}\n'
        f'• Cookie file: {yt_dlp_cookie}\n'
        f'• Proxy: {proxy}\n'
        f'• Active sponsors: {sponsor_count}\n'
        f"• Queue workers: {queue_stats.get('workers', 0)}\n"
        f"• Queue active/waiting: {queue_stats.get('active', 0)}/{queue_stats.get('waiting', 0)}\n"
        f'• Free daily limit: {db.get_free_daily_limit(settings.free_daily_limit)}\n'
    )
