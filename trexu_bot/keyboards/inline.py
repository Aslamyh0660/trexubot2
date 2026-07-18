from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import VIPPlan
from ..i18n import t


def sponsor_join_keyboard(channels: list[dict[str, str]], lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(channel['title'], url=channel['invite_link'])] for channel in channels]
    rows.append([InlineKeyboardButton(t('joined_check', lang), callback_data='force:check')])
    return InlineKeyboardMarkup(rows)


def music_result_keyboard(token: str, page: int, total: int, add_playlist: bool = False) -> InlineKeyboardMarkup:
    nav_row = [
        InlineKeyboardButton('⬅️', callback_data=f'msr:prev:{token}:{page}'),
        InlineKeyboardButton(f'{page + 1}/{total}', callback_data='noop'),
        InlineKeyboardButton('➡️', callback_data=f'msr:next:{token}:{page}'),
    ]
    rows = [
        nav_row,
        [InlineKeyboardButton('✅ انتخاب و دانلود', callback_data=f'msr:pick:{token}:{page}')],
    ]
    if add_playlist:
        rows.append([InlineKeyboardButton('➕ افزودن به پلی‌لیست', callback_data=f'msr:add:{token}:{page}')])
    return InlineKeyboardMarkup(rows)


def track_actions_keyboard(token: str, share_text: str | None = None, can_add_playlist: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton('📥 دانلود آهنگ', callback_data=f'track:download:{token}')],
        [
            InlineKeyboardButton('📝 متن آهنگ', callback_data=f'track:lyrics:{token}'),
            InlineKeyboardButton('🎵 مشابه', callback_data=f'track:similar:{token}'),
        ],
    ]
    if can_add_playlist:
        rows.append([InlineKeyboardButton('➕ افزودن به پلی‌لیست', callback_data=f'track:playlist:{token}')])
    rows.append([
        InlineKeyboardButton('🔗 اشتراک‌گذاری', switch_inline_query=share_text or 'Trexu Bot')
    ])
    return InlineKeyboardMarkup(rows)


def downloader_preview_keyboard(token: str, is_vip: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton('360p', callback_data=f'dl:video:{token}:360'),
            InlineKeyboardButton('720p', callback_data=f'dl:video:{token}:720'),
            InlineKeyboardButton('1080p', callback_data=f'dl:video:{token}:1080'),
        ],
        [InlineKeyboardButton('🎵 تبدیل به MP3', callback_data=f'dl:audio:{token}:mp3')],
        [InlineKeyboardButton('🔍 تشخیص آهنگ از ویدئو', callback_data=f'dl:recognize:{token}:na')],
        [InlineKeyboardButton('📋 لینک مستقیم', callback_data=f'dl:copy:{token}:na')],
    ]
    if not is_vip:
        rows.append([InlineKeyboardButton('💎 کیفیت 1080p مخصوص VIP', callback_data='vip:show')])
    return InlineKeyboardMarkup(rows)


def vip_plans_keyboard(plans: dict[str, VIPPlan], lang: str) -> InlineKeyboardMarkup:
    rows = []
    for code, plan in plans.items():
        title = plan.title_fa if lang == 'fa' else plan.title_en
        rows.append([InlineKeyboardButton(f'{title} - {plan.price:,}', callback_data=f'vip:plan:{code}')])
    return InlineKeyboardMarkup(rows)


def payment_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ تأیید', callback_data=f'pay:approve:{payment_id}'),
            InlineKeyboardButton('❌ رد', callback_data=f'pay:reject:{payment_id}'),
        ]
    ])
