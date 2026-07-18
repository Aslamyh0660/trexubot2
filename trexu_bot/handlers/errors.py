from __future__ import annotations

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error('Exception while handling update: %s', context.error)
    tb = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(tb)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                '❌ خطایی در پردازش درخواست رخ داد. لطفاً دوباره تلاش کن.'
            )
        except Exception:
            logger.exception('Failed to send error message to user')
