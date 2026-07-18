from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t

HandlerFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]


def admin_required(func: HandlerFn) -> HandlerFn:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        db = context.application.bot_data['db']
        user = update.effective_user
        if not user or not db.is_admin(user.id):
            lang = db.get_user_lang(user.id if user else 0)
            if update.effective_message:
                await update.effective_message.reply_text(t('admin_only', lang))
            return None
        return await func(update, context)

    return wrapper  # type: ignore[return-value]
