from __future__ import annotations

from pathlib import Path

from telegram import InputFile, Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.inline import downloader_preview_keyboard
from ..services.ads import maybe_send_free_user_ad
from ..utils.helpers import format_duration, make_token
from ..utils.progress import ProgressContext
from . import music as music_handler


async def preview_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    db = context.application.bot_data['db']
    downloader = context.application.bot_data['downloader']
    info = await downloader.extract_info(url)
    token = make_token(8)
    context.user_data.setdefault('pending_downloads', {})[token] = info
    is_vip = bool((db.get_account_snapshot(user.id) or {}).get('is_vip'))

    caption = (
        f"🎬 *{info['title']}*\n"
        f"⏱ مدت: {format_duration(info.get('duration'))}\n"
        f"📺 پلتفرم: {info.get('extractor')}\n"
        f"👤 ناشر: {info.get('uploader') or '-'}"
    )
    keyboard = downloader_preview_keyboard(token, is_vip=is_vip)
    if info.get('thumbnail'):
        await context.bot.send_photo(
            chat_id=message.chat_id,
            photo=info['thumbnail'],
            caption=caption,
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
    else:
        await message.reply_text(caption, parse_mode='Markdown', reply_markup=keyboard)


async def execute_download(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, kind: str, quality: str) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    downloader = context.application.bot_data['downloader']
    queue_service = context.application.bot_data['queue_service']
    lang = db.get_user_lang(user.id)
    info = context.user_data.get('pending_downloads', {}).get(token)
    if not info:
        await query.answer('Expired preview', show_alert=True)
        return

    snapshot = db.get_account_snapshot(user.id) or {}
    is_vip = bool(snapshot.get('is_vip'))
    if kind == 'video' and quality == '1080' and not is_vip:
        await query.answer('کیفیت 1080p فقط برای VIP است.', show_alert=True)
        return

    allowed, _ = db.can_user_download(user.id, db.get_free_daily_limit(settings.free_daily_limit))
    if not allowed:
        await query.answer(t('daily_limit_reached', lang), show_alert=True)
        return

    file_kind = f'video_{quality}' if kind == 'video' else 'audio_mp3'
    format_code = quality if kind == 'video' else 'mp3'
    cache = db.find_cached_download(info['webpage_url'], file_kind, format_code)
    if cache and Path(cache.file_path).exists():
        await query.answer(t('cache_hit', lang), show_alert=False)
        with open(cache.file_path, 'rb') as f:
            if kind == 'video':
                sent = await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=InputFile(f, filename=Path(cache.file_path).name),
                    caption=f"🎬 {cache.title or info['title']}\n⚡️ {t('cache_hit', lang)}",
                )
                file_id = sent.video.file_id if sent.video else None
            else:
                sent = await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=InputFile(f, filename=Path(cache.file_path).name),
                    title=cache.title or info['title'],
                    performer=cache.artist or info.get('uploader'),
                    caption=f"🎵 {cache.title or info['title']}\n⚡️ {t('cache_hit', lang)}",
                )
                file_id = sent.audio.file_id if sent.audio else None
        db.register_download_usage(user.id, db.get_free_daily_limit(settings.free_daily_limit))
        db.save_download_record(
            user_tg_id=user.id,
            source_url=info['webpage_url'],
            platform=info['extractor'],
            title=cache.title or info['title'],
            artist=cache.artist or info.get('uploader'),
            file_path=cache.file_path,
            file_kind=file_kind,
            format_code=format_code,
            telegram_file_id=file_id,
        )
        await maybe_send_free_user_ad(context, user.id, query.message.chat_id)
        return

    progress_message = await query.message.reply_text(t('queue_busy', lang))
    job_id = f'dl:{user.id}:{make_token(6)}'

    async def job() -> None:
        try:
            progress = ProgressContext(
                bot=context.bot,
                loop=context.application.bot_data['loop'],
                chat_id=query.message.chat_id,
                message_id=progress_message.message_id,
                title=info['title'],
            )
            result = await downloader.download(info['webpage_url'], info['title'], mode=kind, quality=quality, progress=progress)
            with open(result['file_path'], 'rb') as f:
                if kind == 'video':
                    sent = await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=InputFile(f, filename=Path(result['file_path']).name),
                        caption=f"🎬 {result['title']}",
                    )
                    file_id = sent.video.file_id if sent.video else None
                else:
                    sent = await context.bot.send_audio(
                        chat_id=query.message.chat_id,
                        audio=InputFile(f, filename=Path(result['file_path']).name),
                        title=result['title'],
                        performer=result.get('uploader'),
                        caption=f"🎵 {result['title']}",
                    )
                    file_id = sent.audio.file_id if sent.audio else None

            db.register_download_usage(user.id, db.get_free_daily_limit(settings.free_daily_limit))
            db.save_download_record(
                user_tg_id=user.id,
                source_url=result['source_url'],
                platform=result['platform'],
                title=result['title'],
                artist=result.get('uploader'),
                file_path=result['file_path'],
                file_kind=file_kind,
                format_code=format_code,
                telegram_file_id=file_id,
            )
            await maybe_send_free_user_ad(context, user.id, query.message.chat_id)
            try:
                await progress_message.delete()
            except Exception:
                pass
        except Exception:
            try:
                await progress_message.edit_text('❌ دانلود فایل با خطا مواجه شد. دوباره تلاش کن.')
            except Exception:
                pass
            raise

    position = await queue_service.enqueue(
        job_id=job_id,
        vip=is_vip,
        description=f'{kind}:{info["title"]}:{quality}',
        coro_factory=job,
    )
    await progress_message.edit_text(t('queued_download', lang, position=position))


async def execute_recognition(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    downloader = context.application.bot_data['downloader']
    music_service = context.application.bot_data['music_service']
    queue_service = context.application.bot_data['queue_service']
    info = context.user_data.get('pending_downloads', {}).get(token)
    if not info:
        await query.answer('Expired preview', show_alert=True)
        return

    snapshot = db.get_account_snapshot(user.id) or {}
    is_vip = bool(snapshot.get('is_vip'))
    status = await query.message.reply_text(t('queue_busy', lang))
    job_id = f'rec:{user.id}:{make_token(6)}'

    async def job() -> None:
        try:
            await status.edit_text(t('recognizing', lang))
            audio_path = await downloader.download_audio_for_recognition(info['webpage_url'], info['title'])
            result = await music_service.recognize_file(audio_path)
            if not result:
                await status.edit_text(t('recognition_failed', lang))
                return
            try:
                await status.delete()
            except Exception:
                pass
            await music_handler.send_track_card(update, context, result)
        except Exception:
            try:
                await status.edit_text('❌ تشخیص آهنگ از ویدئو با خطا مواجه شد.')
            except Exception:
                pass
            raise

    position = await queue_service.enqueue(
        job_id=job_id,
        vip=is_vip,
        description=f'recognize:{info["title"]}',
        coro_factory=job,
    )
    await status.edit_text(t('queued_download', lang, position=position))
