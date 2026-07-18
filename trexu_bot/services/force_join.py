from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ApplicationHandlerStop, ContextTypes

from ..i18n import t
from ..keyboards.inline import sponsor_join_keyboard

logger = logging.getLogger(__name__)


async def user_joined_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return True

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']

    if settings.force_join_skip_admins and db.is_admin(user.id):
        return True

    channels = db.list_sponsors(active_only=True)
    if not channels:
        return True

    bot = context.bot
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel.chat_id, user.id)
            if member.status in {
                ChatMemberStatus.LEFT,
                ChatMemberStatus.KICKED,
                ChatMemberStatus.RESTRICTED,
            }:
                return False
        except Exception as exc:
            logger.warning('Could not check sponsor membership for user=%s channel=%s error=%s', user.id, channel.chat_id, exc)
            return False
    return True


async def send_force_join_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id if user else 0)
    channels = db.list_sponsors(active_only=True)
    if not channels:
        return

    keyboard = sponsor_join_keyboard(
        [
            {
                'title': channel.title,
                'invite_link': channel.invite_link,
            }
            for channel in channels
        ],
        lang,
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(t('not_joined', lang), reply_markup=keyboard)
    elif update.effective_message:
        await update.effective_message.reply_text(t('not_joined', lang), reply_markup=keyboard)


async def message_gatekeeper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.first_name)

    if db.is_banned(user.id):
        await update.effective_message.reply_text(t('banned', db.get_user_lang(user.id)))
        raise ApplicationHandlerStop

    if not db.bot_enabled() and not db.is_admin(user.id):
        lang = db.get_user_lang(user.id)
        key = 'off_message_fa' if lang == 'fa' else 'off_message_en'
        message = db.get_setting(key, t('bot_off', lang)) or t('bot_off', lang)
        await update.effective_message.reply_text(message)
        raise ApplicationHandlerStop

    if not await user_joined_all(update, context):
        await send_force_join_prompt(update, context)
        raise ApplicationHandlerStop


async def callback_gatekeeper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.callback_query:
        return

    db = context.application.bot_data['db']
    user = update.effective_user
    if db.is_banned(user.id):
        await update.callback_query.answer(t('banned', db.get_user_lang(user.id)), show_alert=True)
        raise ApplicationHandlerStop

    if not db.bot_enabled() and not db.is_admin(user.id):
        lang = db.get_user_lang(user.id)
        key = 'off_message_fa' if lang == 'fa' else 'off_message_en'
        message = db.get_setting(key, t('bot_off', lang)) or t('bot_off', lang)
        await update.callback_query.answer(message, show_alert=True)
        raise ApplicationHandlerStop

    if not await user_joined_all(update, context):
        await send_force_join_prompt(update, context)
        raise ApplicationHandlerStop
