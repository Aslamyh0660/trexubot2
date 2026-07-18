from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiohttp

from ..config import Settings

logger = logging.getLogger(__name__)


class MusicService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def recognize_file(self, file_path: str | Path) -> dict[str, Any] | None:
        if not self.settings.audd_api_token:
            logger.warning('AUDD_API_TOKEN is not set')
            return None

        file_path = str(file_path)
        url = 'https://api.audd.io/'
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)
        data = aiohttp.FormData()
        data.add_field('api_token', self.settings.audd_api_token)
        data.add_field('return', 'apple_music,spotify,deezer,lyrics')
        with open(file_path, 'rb') as f:
            data.add_field('file', f, filename=Path(file_path).name, content_type='application/octet-stream')
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, data=data) as resp:
                    payload = await resp.json(content_type=None)

        result = payload.get('result') if isinstance(payload, dict) else None
        if not result:
            return None

        artwork = None
        album = result.get('album')
        external_url = None

        apple_music = result.get('apple_music') or {}
        spotify = result.get('spotify') or {}
        deezer = result.get('deezer') or {}
        if apple_music.get('artwork', {}).get('url'):
            artwork = apple_music['artwork']['url'].replace('{w}', '800').replace('{h}', '800')
        elif spotify.get('album', {}).get('images'):
            artwork = spotify['album']['images'][0].get('url')
        elif deezer.get('album', {}).get('cover_xl'):
            artwork = deezer['album']['cover_xl']
        external_url = spotify.get('external_urls', {}).get('spotify') or deezer.get('link') or apple_music.get('url')

        return {
            'artist': result.get('artist'),
            'title': result.get('title'),
            'album': album,
            'release_date': result.get('release_date'),
            'artwork': artwork,
            'external_url': external_url,
            'lyrics': result.get('lyrics', {}).get('lyrics') if result.get('lyrics') else None,
        }

    async def search_tracks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)
        url = 'https://api.deezer.com/search'
        params = {'q': query, 'limit': str(limit)}
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                payload = await resp.json(content_type=None)
        items = []
        for row in payload.get('data', []):
            items.append(
                {
                    'title': row.get('title'),
                    'artist': row.get('artist', {}).get('name'),
                    'album': row.get('album', {}).get('title'),
                    'artwork': row.get('album', {}).get('cover_xl') or row.get('album', {}).get('cover_big'),
                    'preview': row.get('preview'),
                    'deezer_url': row.get('link'),
                    'artist_id': row.get('artist', {}).get('id'),
                }
            )
        return items

    async def get_similar_tracks(self, artist: str, limit: int = 5) -> list[dict[str, Any]]:
        # Practical fallback: fetch more tracks by the same artist from Deezer search.
        return await self.search_tracks(artist, limit=limit)

    async def get_lyrics(self, artist: str, title: str) -> str | None:
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)

        if self.settings.genius_api_token:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(
                        'https://api.genius.com/search',
                        headers={'Authorization': f'Bearer {self.settings.genius_api_token}'},
                        params={'q': f'{artist} {title}'},
                    ) as resp:
                        payload = await resp.json(content_type=None)
                hits = payload.get('response', {}).get('hits', []) if isinstance(payload, dict) else []
                if hits:
                    best = hits[0].get('result', {})
                    maybe_description = best.get('description', {}).get('plain')
                    if maybe_description:
                        return maybe_description
            except Exception:
                logger.exception('Genius search failed')

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f'https://api.lyrics.ovh/v1/{artist}/{title}') as resp:
                    if resp.status == 200:
                        payload = await resp.json(content_type=None)
                        lyrics = payload.get('lyrics')
                        if lyrics:
                            return lyrics[:4000]
        except Exception:
            logger.exception('Lyrics fallback failed')
        return None
