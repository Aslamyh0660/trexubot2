from __future__ import annotations

import logging

from telegram.ext import ContextTypes

from .services.cleanup import cleanup_old_files

logger = logging.getLogger(__name__)


async def vip_expiry_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data['db']
    users = db.expiring_vips(within_days=3)
    for user in users:
        if user.vip_expiry_notified_at:
            continue
        try:
            await context.bot.send_message(user.tg_id, '⏰ اشتراک VIP شما تا ۳ روز دیگر منقضی می‌شود. برای تمدید از بخش VIP استفاده کن.')
            db.mark_expiry_notified(user.tg_id)
        except Exception:
            logger.exception('Failed to send VIP expiry reminder to %s', user.tg_id)


async def cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = context.application.bot_data['config']
    removed = cleanup_old_files([settings.download_dir, settings.temp_dir], settings.max_file_age_days)
    logger.info('Cleanup complete, removed %s old files', removed)
