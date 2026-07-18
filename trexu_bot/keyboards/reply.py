from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

from ..i18n import t


def main_menu(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(t('menu_search', lang)), KeyboardButton(t('menu_downloader', lang))],
        [KeyboardButton(t('menu_vip', lang)), KeyboardButton(t('menu_account', lang))],
        [KeyboardButton(t('menu_history', lang)), KeyboardButton(t('menu_playlist', lang))],
        [KeyboardButton(t('menu_channel', lang)), KeyboardButton(t('menu_add_group', lang))],
        [KeyboardButton(t('menu_language', lang))],
    ]
    if is_admin:
        rows.append([KeyboardButton(t('admin_panel', lang))])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def admin_menu(lang: str) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton('📊 آمار'), KeyboardButton('📣 برادکست')],
        [KeyboardButton('💳 تنظیم کارت'), KeyboardButton('🎯 محدودیت روزانه')],
        [KeyboardButton('📡 اسپانسرها'), KeyboardButton('🧾 پرداخت‌های معلق')],
        [KeyboardButton('📢 تبلیغ رایگان'), KeyboardButton('🩺 سلامت ربات')],
        [KeyboardButton('🔴 خاموش کردن ربات'), KeyboardButton('🟢 روشن کردن ربات')],
        [KeyboardButton('✉️ پیام خوش‌آمد'), KeyboardButton('⚙️ پیام‌های سیستمی')],
        [KeyboardButton('👤 مدیریت کاربران'), KeyboardButton(t('back', lang))],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def language_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton('فارسی'), KeyboardButton('English')]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton(t('cancel', lang)), KeyboardButton(t('back', lang))]], resize_keyboard=True)
