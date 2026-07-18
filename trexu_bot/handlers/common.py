from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.inline import vip_plans_keyboard
from ..keyboards.reply import admin_menu, language_menu, main_menu
from ..services.referral import build_ref_link
from ..utils.helpers import is_url
from . import admin as admin_handler
from . import downloader as downloader_handler
from . import music as music_handler


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str | None = None) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    await update.effective_message.reply_text(
        text or t('send_link_or_media', lang),
        reply_markup=main_menu(lang, is_admin=db.is_admin(user.id)),
        disable_web_page_preview=True,
    )


async def show_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    snapshot = db.get_account_snapshot(user.id)
    if not snapshot:
        return
    lang = snapshot['language']
    bot_username = (await context.bot.get_me()).username
    ref_link = build_ref_link(bot_username, snapshot['referral_code'])

    if snapshot['is_vip'] and snapshot['vip_until']:
        sub_line = t('subscription_active', lang, date=snapshot['vip_until'].strftime('%Y-%m-%d %H:%M'))
    else:
        sub_line = t('subscription_none', lang)

    text = (
        f"{t('account_info', lang)}\n\n"
        f"🆔 ID: {snapshot['tg_id']}\n"
        f"👤 Username: @{snapshot['username'] or '-'}\n"
        f"🌐 Lang: {snapshot['language']}\n"
        f"{sub_line}\n"
        f"📥 Today: {snapshot['daily_downloads']}\n"
        f"🎁 Referral count: {snapshot['referrals_count']}\n"
        f"⚡ Credits: {snapshot['extra_download_credits']}\n\n"
        f"{t('referral_text', lang, link=ref_link)}"
    )
    await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    rows = db.recent_history(user.id)
    if not rows:
        await update.effective_message.reply_text(t('history_empty', lang))
        return
    lines = ['📜 آخرین دانلودها:']
    for item in rows:
        created = item.created_at.strftime('%m-%d %H:%M') if isinstance(item.created_at, datetime) else '-'
        lines.append(f'• {item.title or "بدون عنوان"} | {item.platform} | {created}')
    await update.effective_message.reply_text('\n'.join(lines))


async def show_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    rows = db.list_playlist(user.id)
    if not rows:
        await update.effective_message.reply_text(t('playlist_empty', lang))
        return
    lines = ['🎼 پلی‌لیست شخصی شما:']
    for idx, item in enumerate(rows, start=1):
        lines.append(f'{idx}. {item.title} - {item.artist or "Unknown"}')
    await update.effective_message.reply_text('\n'.join(lines), disable_web_page_preview=True)


async def show_vip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    settings = context.application.bot_data['config']
    if update.effective_message:
        await update.effective_message.reply_text(
            f"{t('vip_benefits', lang)}\n\n{t('choose_vip_plan', lang)}",
            reply_markup=vip_plans_keyboard(settings.vip_plans, lang),
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            f"{t('vip_benefits', lang)}\n\n{t('choose_vip_plan', lang)}",
            reply_markup=vip_plans_keyboard(settings.vip_plans, lang),
        )


async def show_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    settings = context.application.bot_data['config']
    await update.effective_message.reply_text(t('channel_link', lang, url=settings.channel_url), disable_web_page_preview=True)


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db = context.application.bot_data['db']
    await update.effective_message.reply_text(t('choose_language', db.get_user_lang(user.id)), reply_markup=language_menu())


async def apply_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user or not update.effective_message:
        return False
    text = (update.effective_message.text or '').strip().lower()
    db = context.application.bot_data['db']
    if text in {'فارسی', 'fa', 'persian'}:
        db.set_user_lang(user.id, 'fa')
        await update.effective_message.reply_text(t('language_updated', 'fa'), reply_markup=main_menu('fa', is_admin=db.is_admin(user.id)))
        return True
    if text in {'english', 'en'}:
        db.set_user_lang(user.id, 'en')
        await update.effective_message.reply_text(t('language_updated', 'en'), reply_markup=main_menu('en', is_admin=db.is_admin(user.id)))
        return True
    return False


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not message.text:
        return

    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    text = message.text.strip()

    if await apply_language_selection(update, context):
        return

    if text == t('cancel', lang):
        context.user_data.clear()
        await send_main_menu(update, context, t('operation_cancelled', lang))
        return

    if text == t('back', lang):
        context.user_data.pop('mode', None)
        context.user_data.pop('admin_action', None)
        await send_main_menu(update, context)
        return

    if db.is_admin(user.id) and context.user_data.get('admin_action'):
        await admin_handler.handle_pending_admin_action(update, context)
        return

    if text == t('menu_search', lang):
        context.user_data['mode'] = 'music_search'
        await message.reply_text(t('start_search', lang))
        return

    if text == t('menu_downloader', lang):
        context.user_data['mode'] = 'downloader'
        await message.reply_text(t('start_downloader', lang))
        return

    if text == t('menu_vip', lang):
        await show_vip(update, context)
        return

    if text == t('menu_account', lang):
        await show_account(update, context)
        return

    if text == t('menu_history', lang):
        await show_history(update, context)
        return

    if text == t('menu_playlist', lang):
        await show_playlist(update, context)
        return

    if text == t('menu_channel', lang):
        await show_channel(update, context)
        return

    if text == t('menu_add_group', lang):
        await message.reply_text(t('help_group', lang))
        return

    if text == t('menu_language', lang):
        await change_language(update, context)
        return

    if db.is_admin(user.id) and text == t('admin_panel', lang):
        await message.reply_text('پنل مدیریت باز شد.', reply_markup=admin_menu(lang))
        return

    if db.is_admin(user.id) and text in {
        '📊 آمار', '📣 برادکست', '💳 تنظیم کارت', '🎯 محدودیت روزانه', '📡 اسپانسرها',
        '🧾 پرداخت‌های معلق', '📢 تبلیغ رایگان', '🩺 سلامت ربات', '🔴 خاموش کردن ربات',
        '🟢 روشن کردن ربات', '✉️ پیام خوش‌آمد', '⚙️ پیام‌های سیستمی', '👤 مدیریت کاربران'
    }:
        await admin_handler.admin_menu_router(update, context)
        return

    if is_url(text):
        await downloader_handler.preview_url(update, context, text)
        return

    if context.user_data.get('mode') == 'music_search':
        await music_handler.perform_music_search(update, context, text)
        return

    if context.user_data.get('mode') == 'downloader':
        await downloader_handler.preview_url(update, context, text)
        return

    await message.reply_text(t('unknown_command', lang), reply_markup=main_menu(lang, is_admin=db.is_admin(user.id)))
