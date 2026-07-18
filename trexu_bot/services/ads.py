from __future__ import annotations

from telegram.ext import ContextTypes


async def maybe_send_free_user_ad(context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> None:
    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    snapshot = db.get_account_snapshot(user_id)
    if not snapshot or snapshot.get('is_vip'):
        return

    interval = db.get_ad_interval(settings.free_ad_interval)
    if interval <= 0:
        return

    total_downloads = db.count_user_downloads(user_id)
    if total_downloads <= 0 or total_downloads % interval != 0:
        return

    lang = snapshot['language']
    key = 'free_ad_message_fa' if lang == 'fa' else 'free_ad_message_en'
    fallback = (
        '📢 حمایت از Trexu Bot\n\n'
        'برای حذف تبلیغ، دانلود نامحدود و کیفیت 1080p از بخش VIP استفاده کن.'
        if lang == 'fa'
        else '📢 Support Trexu Bot\n\nUpgrade to VIP for ad-free unlimited downloads and 1080p quality.'
    )
    message = db.get_setting(key, fallback) or fallback
    await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
