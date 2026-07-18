from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.reply import main_menu


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    db_user = db.get_or_create_user(user.id, user.username, user.first_name, settings.default_lang)

    if context.args:
        arg = context.args[0]
        if arg.startswith('ref_'):
            db.process_referral(user.id, arg.replace('ref_', '', 1))

    lang = db_user.language
    welcome_key = 'welcome_message_fa' if lang == 'fa' else 'welcome_message_en'
    welcome_message = db.get_setting(welcome_key, t('welcome', lang)) or t('welcome', lang)

    await update.effective_message.reply_text(
        welcome_message,
        reply_markup=main_menu(lang, is_admin=db.is_admin(user.id)),
        disable_web_page_preview=True,
    )
