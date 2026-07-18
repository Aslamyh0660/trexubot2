from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t
from . import common as common_handler
from . import downloader as downloader_handler
from . import music as music_handler
from . import payments as payment_handler


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    lang = db.get_user_lang(user.id)
    data = query.data or ''

    if data == 'noop':
        await query.answer()
        return

    if data == 'force:check':
        from ..services.force_join import user_joined_all
        if await user_joined_all(update, context):
            await query.answer(t('membership_ok', lang), show_alert=True)
            await query.message.reply_text('✅ عضویت شما تأیید شد.')
        else:
            await query.answer(t('join_failed', lang), show_alert=True)
        return

    if data.startswith('msr:'):
        _, action, token, page_raw = data.split(':', 3)
        page = int(page_raw)
        payload = context.user_data.get('music_search', {}).get(token)
        if not payload:
            await query.answer('Expired', show_alert=True)
            return
        total = len(payload['results'])
        if action == 'prev':
            new_page = (page - 1) % total
            await query.answer()
            await music_handler.render_search_page(query.message.chat_id, context, token, new_page, message_id=query.message.message_id)
            return
        if action == 'next':
            new_page = (page + 1) % total
            await query.answer()
            await music_handler.render_search_page(query.message.chat_id, context, token, new_page, message_id=query.message.message_id)
            return
        if action == 'pick':
            await query.answer('در حال دانلود...')
            await music_handler.send_selected_search_track(update, context, token, page)
            return
        if action == 'add':
            await music_handler.add_search_track_to_playlist(update, context, token, page)
            return

    if data.startswith('track:'):
        _, action, token = data.split(':', 2)
        track = context.user_data.get('tracks', {}).get(token)
        if not track:
            await query.answer('Expired', show_alert=True)
            return
        title = track.get('title') or 'Unknown'
        artist = track.get('artist') or 'Unknown'

        if action == 'lyrics':
            await query.answer('Lyrics...')
            lyrics = track.get('lyrics') or await context.application.bot_data['music_service'].get_lyrics(artist, title)
            if not lyrics:
                await query.message.reply_text(t('lyrics_not_found', lang))
            else:
                await query.message.reply_text(f'📝 {title} - {artist}\n\n{lyrics[:4000]}')
            return

        if action == 'similar':
            await query.answer('Similar...')
            rows = await context.application.bot_data['music_service'].get_similar_tracks(artist, limit=5)
            if not rows:
                await query.message.reply_text(t('search_no_result', lang))
                return
            lines = [f'🎵 آهنگ‌های مشابه برای {artist}:']
            for item in rows[:5]:
                lines.append(f"• {item.get('title')} - {item.get('artist')}")
            await query.message.reply_text('\n'.join(lines))
            return

        if action == 'playlist':
            db.add_playlist_item(user.id, title, artist, track.get('external_url'), track.get('artwork'))
            await query.answer(t('playlist_added', lang), show_alert=True)
            return

        if action == 'download':
            await query.answer('Downloading...')
            await music_handler.download_and_send_track(
                update,
                context,
                title=title,
                artist=artist,
                album=track.get('album'),
                artwork=track.get('artwork'),
                source_url=track.get('external_url'),
            )
            return

    if data.startswith('dl:'):
        _, action, token, quality = data.split(':', 3)
        if action == 'video':
            await query.answer('شروع دانلود ویدئو...')
            await downloader_handler.execute_download(update, context, token, 'video', quality)
            return
        if action == 'audio':
            await query.answer('شروع دانلود MP3...')
            await downloader_handler.execute_download(update, context, token, 'audio', 'mp3')
            return
        if action == 'recognize':
            await query.answer('در حال تشخیص...')
            await downloader_handler.execute_recognition(update, context, token)
            return
        if action == 'copy':
            info = context.user_data.get('pending_downloads', {}).get(token)
            if info:
                await query.message.reply_text(t('copied_link', lang, url=info['webpage_url']), disable_web_page_preview=True)
            await query.answer()
            return

    if data == 'vip:show':
        await query.answer()
        await common_handler.show_vip(update, context)
        return

    if data.startswith('vip:plan:'):
        _, _, plan_code = data.split(':', 2)
        await query.answer('پلن انتخاب شد.')
        await payment_handler.prompt_payment_receipt(update, context, plan_code)
        return

    if data.startswith('pay:'):
        if not db.is_admin(user.id):
            await query.answer(t('admin_only', lang), show_alert=True)
            return
        _, action, payment_id_raw = data.split(':', 2)
        payment_id = int(payment_id_raw)
        payment = db.get_payment(payment_id)
        if not payment:
            await query.answer('Payment not found', show_alert=True)
            return

        plan = settings.vip_plans.get(payment.plan_code)
        if not plan:
            await query.answer('Plan not found', show_alert=True)
            return

        pay_user = db.get_user_by_payment(payment_id)
        if not pay_user:
            await query.answer('User not found', show_alert=True)
            return

        if action == 'approve':
            approved = db.approve_payment(payment_id, user.id, plan.days)
            if not approved:
                await query.answer('Already reviewed', show_alert=True)
                return
            await query.answer('Approved ✅', show_alert=True)
            await query.message.reply_text(f'پرداخت {payment_id} تأیید شد ✅')
            try:
                await context.bot.send_message(pay_user.tg_id, t('payment_approved', db.get_user_lang(pay_user.tg_id)))
            except Exception:
                pass
            return

        if action == 'reject':
            rejected = db.reject_payment(payment_id, user.id)
            if not rejected:
                await query.answer('Already reviewed', show_alert=True)
                return
            await query.answer('Rejected ❌', show_alert=True)
            await query.message.reply_text(f'پرداخت {payment_id} رد شد ❌')
            try:
                await context.bot.send_message(pay_user.tg_id, t('payment_rejected', db.get_user_lang(pay_user.tg_id)))
            except Exception:
                pass
            return

    await query.answer()
