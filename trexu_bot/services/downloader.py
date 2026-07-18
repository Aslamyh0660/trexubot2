from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import yt_dlp

from ..config import Settings
from ..utils.helpers import extract_platform, sanitize_filename
from ..utils.progress import ProgressContext

logger = logging.getLogger(__name__)


class DownloaderService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.download_dir.mkdir(parents=True, exist_ok=True)
        self.settings.temp_dir.mkdir(parents=True, exist_ok=True)

    def _base_opts(self) -> dict[str, Any]:
        opts: dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'socket_timeout': self.settings.request_timeout,
        }
        if self.settings.yt_dlp_cookie_file:
            opts['cookiefile'] = self.settings.yt_dlp_cookie_file
        if self.settings.proxy_url:
            opts['proxy'] = self.settings.proxy_url
        return opts

    async def extract_info(self, url: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._extract_info_sync, url)

    def _extract_info_sync(self, url: str) -> dict[str, Any]:
        opts = self._base_opts()
        opts.update({'skip_download': True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and 'entries' in info and info['entries']:
            info = info['entries'][0]
        if not info:
            raise ValueError('No media info extracted')
        return {
            'title': info.get('title') or 'Unknown',
            'duration': info.get('duration') or 0,
            'thumbnail': info.get('thumbnail'),
            'webpage_url': info.get('webpage_url') or url,
            'extractor': info.get('extractor_key') or info.get('extractor') or 'direct',
            'uploader': info.get('uploader') or info.get('channel') or info.get('artist'),
            'description': info.get('description'),
            'id': info.get('id'),
            'filesize': info.get('filesize') or info.get('filesize_approx'),
            'original_url': url,
        }

    async def search_audio(self, query: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._search_audio_sync, query)

    def _search_audio_sync(self, query: str) -> dict[str, Any]:
        opts = self._base_opts()
        opts.update({'skip_download': True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f'ytsearch1:{query}', download=False)
        if not info or not info.get('entries'):
            raise ValueError('No search result found')
        entry = info['entries'][0]
        return {
            'title': entry.get('title') or query,
            'duration': entry.get('duration') or 0,
            'thumbnail': entry.get('thumbnail'),
            'webpage_url': entry.get('webpage_url'),
            'extractor': entry.get('extractor_key') or 'youtube',
            'uploader': entry.get('uploader') or entry.get('channel') or entry.get('artist'),
            'id': entry.get('id'),
            'filesize': entry.get('filesize') or entry.get('filesize_approx'),
            'original_url': entry.get('webpage_url'),
        }

    async def download(self, url: str, title_hint: str, mode: str, quality: str, progress: ProgressContext | None = None) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._download_sync, url, title_hint, mode, quality, progress)

    def _download_sync(self, url: str, title_hint: str, mode: str, quality: str, progress: ProgressContext | None = None) -> dict[str, Any]:
        safe_title = sanitize_filename(title_hint)
        out_dir = self.settings.download_dir / mode
        out_dir.mkdir(parents=True, exist_ok=True)

        if mode == 'audio':
            ext = 'mp3'
            format_selector = 'bestaudio/best'
        else:
            ext = 'mp4'
            height = {'360': 360, '720': 720, '1080': 1080}.get(quality, 720)
            format_selector = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'

        output_template = str(out_dir / f'{safe_title}.%(ext)s')
        opts = self._base_opts()
        opts.update(
            {
                'outtmpl': output_template,
                'format': format_selector,
                'merge_output_format': 'mp4',
                'overwrites': False,
                'restrictfilenames': False,
            }
        )
        if mode == 'audio':
            opts['postprocessors'] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ]
        if progress:
            opts['progress_hooks'] = [progress.hook]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_info = info['entries'][0] if info and 'entries' in info and info['entries'] else info
            prepared = ydl.prepare_filename(final_info)

        file_path = Path(prepared)
        if mode == 'audio':
            file_path = file_path.with_suffix('.mp3')
        elif file_path.suffix.lower() != '.mp4':
            alt = file_path.with_suffix('.mp4')
            if alt.exists():
                file_path = alt

        if not file_path.exists():
            matches = sorted(out_dir.glob(f'{safe_title}*'))
            if not matches:
                raise FileNotFoundError('Downloaded file not found')
            file_path = matches[-1]

        return {
            'file_path': str(file_path),
            'title': final_info.get('title') or title_hint,
            'uploader': final_info.get('uploader') or final_info.get('channel') or final_info.get('artist'),
            'duration': final_info.get('duration') or 0,
            'thumbnail': final_info.get('thumbnail'),
            'platform': extract_platform(url, final_info.get('extractor_key') or final_info.get('extractor')),
            'source_url': final_info.get('webpage_url') or url,
            'file_kind': 'audio_mp3' if mode == 'audio' else f'video_{quality}',
            'format_code': quality if mode == 'video' else 'mp3',
        }

    async def download_audio_for_recognition(self, url: str, title_hint: str) -> str:
        result = await self.download(url=url, title_hint=title_hint, mode='audio', quality='mp3')
        return result['file_path']
