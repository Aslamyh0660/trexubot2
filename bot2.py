from __future__ import annotations

import asyncio
import logging

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from trexu_bot.config import Settings
from trexu_bot.db import DatabaseManager
from trexu_bot.handlers import admin, callbacks, common, errors, music, payments, start
from trexu_bot.jobs import cleanup_job, vip_expiry_reminder_job
from trexu_bot.logging_config import setup_logging
from trexu_bot.services.downloader import DownloaderService
from trexu_bot.services.force_join import callback_gatekeeper, message_gatekeeper
from trexu_bot.services.music import MusicService
from trexu_bot.services.payments import PaymentService
from trexu_bot.services.startup import build_startup_report
from trexu_bot.services.task_queue import DownloadQueueService

logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    application.bot_data['loop'] = asyncio.get_running_loop()

    queue_service: DownloadQueueService = application.bot_data['queue_service']
    await queue_service.start()

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(cleanup_job, interval=60 * 60 * 6, first=30)
        job_queue.run_repeating(vip_expiry_reminder_job, interval=60 * 60 * 24, first=60)

    settings = application.bot_data['config']
    db = application.bot_data['db']
    report = build_startup_report(settings, db, queue_service.stats())
    logger.info(report)
    for admin_id in settings.admin_ids:
        try:
            await application.bot.send_message(admin_id, report)
        except Exception:
            logger.exception('Failed to send startup report to admin %s', admin_id)


async def post_shutdown(application) -> None:
    queue_service: DownloadQueueService = application.bot_data.get('queue_service')
    if queue_service:
        await queue_service.stop()


def build_app():
    setup_logging()
    settings = Settings.from_env()
    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(settings.database_url, admin_ids=settings.admin_ids, default_lang=settings.default_lang)
    db.init_db()

    settings.bank_card_number = db.get_setting('bank_card_number', settings.bank_card_number) or settings.bank_card_number
    settings.bank_card_holder = db.get_setting('bank_card_holder', settings.bank_card_holder) or settings.bank_card_holder
    settings.free_daily_limit = db.get_free_daily_limit(settings.free_daily_limit)
    settings.free_ad_interval = db.get_ad_interval(settings.free_ad_interval)

    app = ApplicationBuilder().token(settings.bot_token).post_init(post_init).post_shutdown(post_shutdown).build()

    app.bot_data['config'] = settings
    app.bot_data['db'] = db
    app.bot_data['downloader'] = DownloaderService(settings)
    app.bot_data['music_service'] = MusicService(settings)
    app.bot_data['payment_service'] = PaymentService(settings)
    app.bot_data['queue_service'] = DownloadQueueService(worker_count=settings.download_workers)

    # Gatekeepers
    app.add_handler(MessageHandler(filters.ALL, message_gatekeeper), group=-1)
    app.add_handler(CallbackQueryHandler(callback_gatekeeper), group=-1)

    # Commands
    app.add_handler(CommandHandler('start', start.start_command))
    app.add_handler(CommandHandler('admin', admin.show_stats))
    app.add_handler(CommandHandler('stats', admin.stats_command))
    app.add_handler(CommandHandler('health', admin.health_command))
    app.add_handler(CommandHandler('ban', admin.ban_command))
    app.add_handler(CommandHandler('unban', admin.unban_command))
    app.add_handler(CommandHandler('vip', admin.vip_command))

    # Media recognition / receipts
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO, music.recognize_media))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, payments.handle_receipt_upload))

    # Main text router
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, common.text_router))

    # Callback router
    app.add_handler(CallbackQueryHandler(callbacks.callback_router))

    app.add_error_handler(errors.error_handler)
    return app


if __name__ == '__main__':
    application = build_app()
    logger.info('Trexu Bot started...')
    application.run_polling(allowed_updates=['message', 'callback_query'])
