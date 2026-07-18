from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from telegram import InputFile, Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.inline import music_result_keyboard, track_actions_keyboard
from ..services.ads import maybe_send_free_user_ad
from ..utils.helpers import make_token
from ..utils.progress import ProgressContext


def _store_track(context: ContextTypes.DEFAULT_TYPE, data: dict[str, Any]) -> str:
    token = make_token(8)
    context.user_data.setdefault('tracks', {})[token] = data
    return token


async def send_track_card(update: Update, context: ContextTypes.DEFAULT_TYPE, track_data: dict[str, Any]) -> None:
    user = update.effective_user
    target_message = update.effective_message if update.effective_message else update.callback_query.message
    if not user or not target_message:
        return

    db = context.application.bot_data['db']
    token = _store_track(context, track_data)
    title = track_data.get('title') or 'Unknown'
    artist = track_data.get('artist') or 'Unknown'
    album = track_data.get('album') or '-'
    caption = f'🎵 *{title}*\n👤 {artist}\n💽 {album}'
    keyboard = track_actions_keyboard(token, share_text=f'{title} - {artist}')
    artwork = track_data.get('artwork')

    if artwork:
        await context.bot.send_photo(
            chat_id=target_message.chat_id,
            photo=artwork,
            caption=caption,
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    else:
        await target_message.reply_text(caption, parse_mode='Markdown', reply_markup=keyboard)


async def recognize_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    music_service = context.application.bot_data['music_service']
    settings = context.application.bot_data['config']

    media = message.voice or message.audio or message.video or message.document
    if not media:
        return

    status = await message.reply_text(t('recognizing', lang))
    telegram_file = await media.get_file()
    ext = '.ogg' if message.voice else '.mp3' if message.audio else '.mp4'
    temp_path = settings.temp_dir / f'music_{user.id}_{make_token(8)}{ext}'
    await telegram_file.download_to_drive(custom_path=str(temp_path))

    try:
        result = await music_service.recognize_file(temp_path)
        if not result:
            await status.edit_text(t('recognition_failed', lang))
            return
        db.save_recognition(
            user_tg_id=user.id,
            artist=result.get('artist'),
            title=result.get('title'),
            album=result.get('album'),
            cover_url=result.get('artwork'),
            external_url=result.get('external_url'),
            source_file_id=getattr(media, 'file_id', None),
        )
        await status.delete()
        await send_track_card(update, context, result)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


async def perform_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    music_service = context.application.bot_data['music_service']

    results = await music_service.search_tracks(query)
    if not results:
        await message.reply_text(t('search_no_result', lang))
        return

    token = make_token(8)
    context.user_data.setdefault('music_search', {})[token] = {'query': query, 'results': results}
    await render_search_page(message.chat_id, context, token, 0)


async def render_search_page(chat_id: int, context: ContextTypes.DEFAULT_TYPE, token: str, page: int, message_id: int | None = None) -> None:
    payload = context.user_data.get('music_search', {}).get(token)
    if not payload:
        return
    results = payload['results']
    total = len(results)
    if total == 0:
        return
    page = max(0, min(page, total - 1))
    item = results[page]
    caption = (
        f"🎵 *{item.get('title') or 'Unknown'}*\n"
        f"👤 {item.get('artist') or 'Unknown'}\n"
        f"💽 {item.get('album') or '-'}\n\n"
        f"{page + 1} / {total}"
    )
    keyboard = music_result_keyboard(token, page, total, add_playlist=True)
    artwork = item.get('artwork')

    if message_id:
        try:
            if artwork:
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    parse_mode='Markdown',
                    reply_markup=keyboard,
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=caption,
                    parse_mode='Markdown',
                    reply_markup=keyboard,
                )
            return
        except Exception:
            pass

    if artwork:
        await context.bot.send_photo(chat_id=chat_id, photo=artwork, caption=caption, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown', reply_markup=keyboard)


async def send_selected_search_track(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, page: int) -> None:
    payload = context.user_data.get('music_search', {}).get(token)
    if not payload:
        return
    results = payload['results']
    if page < 0 or page >= len(results):
        return
    track = results[page]
    await download_and_send_track(
        update,
        context,
        title=track.get('title') or 'Unknown',
        artist=track.get('artist') or 'Unknown',
        album=track.get('album'),
        artwork=track.get('artwork'),
        source_url=track.get('deezer_url'),
    )


async def add_search_track_to_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, page: int) -> None:
    payload = context.user_data.get('music_search', {}).get(token)
    if not payload:
        return
    results = payload['results']
    if page < 0 or page >= len(results):
        return
    user = update.effective_user
    if not user:
        return
    item = results[page]
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    db.add_playlist_item(user.id, item.get('title') or 'Unknown', item.get('artist'), item.get('deezer_url'), item.get('artwork'))
    if update.callback_query:
        await update.callback_query.answer(t('playlist_added', lang), show_alert=True)


async def download_and_send_track(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    title: str,
    artist: str,
    album: str | None = None,
    artwork: str | None = None,
    source_url: str | None = None,
) -> None:
    user = update.effective_user
    message = update.effective_message if update.effective_message else update.callback_query.message
    if not user or not message:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    downloader = context.application.bot_data['downloader']
    queue_service = context.application.bot_data['queue_service']
    lang = db.get_user_lang(user.id)
    snapshot = db.get_account_snapshot(user.id) or {}
    is_vip = bool(snapshot.get('is_vip'))

    allowed, _reason = db.can_user_download(user.id, db.get_free_daily_limit(settings.free_daily_limit))
    if not allowed:
        await message.reply_text(t('daily_limit_reached', lang))
        return

    info = await downloader.search_audio(f'{title} {artist} official audio')
    cache = db.find_cached_download(info['webpage_url'], 'audio_mp3', 'mp3')
    if cache and Path(cache.file_path).exists():
        with open(cache.file_path, 'rb') as f:
            sent = await context.bot.send_audio(
                chat_id=message.chat_id,
                audio=InputFile(f, filename=Path(cache.file_path).name),
                title=title,
                performer=artist,
                caption=f'🎵 {title} - {artist}\n⚡️ {t("cache_hit", lang)}',
            )
        db.register_download_usage(user.id, db.get_free_daily_limit(settings.free_daily_limit))
        db.save_download_record(
            user_tg_id=user.id,
            source_url=info['webpage_url'],
            platform=info['extractor'],
            title=title,
            artist=artist,
            file_path=cache.file_path,
            file_kind='audio_mp3',
            format_code='mp3',
            telegram_file_id=sent.audio.file_id if sent.audio else None,
        )
        await maybe_send_free_user_ad(context, user.id, message.chat_id)
        return

    progress_message = await message.reply_text(t('queue_busy', lang))
    job_id = f'music:{user.id}:{make_token(6)}'

    async def job() -> None:
        try:
            progress = ProgressContext(
                bot=context.bot,
                loop=context.application.bot_data['loop'],
                chat_id=message.chat_id,
                message_id=progress_message.message_id,
                title=title,
            )
            result = await downloader.download(info['webpage_url'], title, mode='audio', quality='mp3', progress=progress)
            with open(result['file_path'], 'rb') as f:
                sent = await context.bot.send_audio(
                    chat_id=message.chat_id,
                    audio=InputFile(f, filename=Path(result['file_path']).name),
                    title=title,
                    performer=artist,
                    caption=f'🎵 {title} - {artist}\n💽 {album or "-"}',
                )

            db.register_download_usage(user.id, db.get_free_daily_limit(settings.free_daily_limit))
            db.save_download_record(
                user_tg_id=user.id,
                source_url=result['source_url'],
                platform=result['platform'],
                title=title,
                artist=artist,
                file_path=result['file_path'],
                file_kind='audio_mp3',
                format_code='mp3',
                telegram_file_id=sent.audio.file_id if sent.audio else None,
            )
            await maybe_send_free_user_ad(context, user.id, message.chat_id)

            track_token = _store_track(
                context,
                {
                    'title': title,
                    'artist': artist,
                    'album': album,
                    'artwork': artwork,
                    'external_url': source_url,
                },
            )
            try:
                await progress_message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=f'🎵 *{title}*\n👤 {artist}\n💽 {album or "-"}',
                parse_mode='Markdown',
                reply_markup=track_actions_keyboard(track_token, share_text=f'{title} - {artist}'),
            )
        except Exception:
            try:
                await progress_message.edit_text('❌ دانلود آهنگ با خطا مواجه شد. دوباره تلاش کن.')
            except Exception:
                pass
            raise

    position = await queue_service.enqueue(
        job_id=job_id,
        vip=is_vip,
        description=f'music:{title}:{artist}',
        coro_factory=job,
    )
    await progress_message.edit_text(t('queued_download', lang, position=position))
