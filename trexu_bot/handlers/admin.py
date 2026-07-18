from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.reply import admin_menu, main_menu
from ..services.broadcaster import broadcast_copy
from ..services.startup import build_startup_report
from ..utils.decorators import admin_required


@admin_required
async def admin_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    text = message.text or ''

    if text == '📊 آمار':
        await show_stats(update, context)
        return
    if text == '📣 برادکست':
        context.user_data['admin_action'] = 'broadcast'
        await message.reply_text('پیام یا رسانه‌ای که باید برای همه ارسال شود را بفرست.')
        return
    if text == '💳 تنظیم کارت':
        context.user_data['admin_action'] = 'set_card'
        await message.reply_text('فرمت: شماره کارت | نام صاحب حساب')
        return
    if text == '🎯 محدودیت روزانه':
        context.user_data['admin_action'] = 'set_limit'
        await message.reply_text('عدد محدودیت دانلود روزانه را بفرست.')
        return
    if text == '📡 اسپانسرها':
        sponsors = db.list_sponsors(active_only=False)
        lines = ['اسپانسرهای فعلی:']
        for item in sponsors:
            lines.append(f'{item.id}) {item.title} | {item.chat_id} | {item.invite_link}')
        lines.append('\nبرای افزودن: add | chat_id | title | invite_link')
        lines.append('برای حذف: remove | sponsor_id')
        context.user_data['admin_action'] = 'manage_sponsors'
        await message.reply_text('\n'.join(lines) if sponsors else 'اسپانسری ثبت نشده.\nadd | chat_id | title | invite_link')
        return
    if text == '🧾 پرداخت‌های معلق':
        pending = db.get_pending_payments()
        if not pending:
            await message.reply_text(t('pending_payments_empty', lang))
            return
        lines = ['پرداخت‌های در انتظار:']
        for row in pending:
            lines.append(f'• ID {row.id} | User {row.user_id} | {row.plan_code} | {row.amount:,}')
        await message.reply_text('\n'.join(lines))
        return
    if text == '📢 تبلیغ رایگان':
        context.user_data['admin_action'] = 'set_free_ad'
        current_interval = db.get_ad_interval(context.application.bot_data['config'].free_ad_interval)
        current_fa = db.get_setting('free_ad_message_fa', '-') or '-'
        await message.reply_text(
            'تبلیغ کاربران رایگان\n\n'
            f'فاصله فعلی نمایش: هر {current_interval} دانلود\n\n'
            f'متن فعلی فارسی:\n{current_fa}\n\n'
            'برای تغییر یکی از این فرمت‌ها را بفرست:\n'
            'interval | 3\n'
            'fa | متن تبلیغ فارسی\n'
            'en | english ad text'
        )
        return
    if text == '🩺 سلامت ربات':
        await health_command(update, context)
        return
    if text == '🔴 خاموش کردن ربات':
        context.user_data['admin_action'] = 'disable_bot'
        await message.reply_text('پیام خاموشی را بفرست تا برای کاربران نمایش داده شود.')
        return
    if text == '🟢 روشن کردن ربات':
        db.set_bot_enabled(True)
        await message.reply_text(t('bot_enabled', lang))
        return
    if text == '✉️ پیام خوش‌آمد':
        context.user_data['admin_action'] = 'set_welcome'
        await message.reply_text('فرمت: fa | متن یا en | text')
        return
    if text == '⚙️ پیام‌های سیستمی':
        dump = db.settings_dump()
        preview = '\n'.join(f'{k}: {v}' for k, v in dump.items())
        context.user_data['admin_action'] = 'set_system_message'
        await message.reply_text(f'تنظیمات فعلی:\n{preview}\n\nفرمت تغییر: key | value')
        return
    if text == '👤 مدیریت کاربران':
        await message.reply_text(
            'دستورات مدیریت کاربران:\n'
            '/ban user_id\n'
            '/unban user_id\n'
            '/vip user_id days\n'
            '/stats'
        )
        return
    if text == t('back', lang):
        await message.reply_text('بازگشت به منوی اصلی', reply_markup=main_menu(lang, is_admin=True))
        return


@admin_required
async def handle_pending_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return

    db = context.application.bot_data['db']
    lang = db.get_user_lang(user.id)
    action = context.user_data.get('admin_action')
    text = message.text or ''

    if action == 'broadcast':
        await message.reply_text(t('broadcast_started', lang))
        result = await broadcast_copy(context.bot, db.list_user_ids(), message.chat_id, message.message_id)
        context.user_data.pop('admin_action', None)
        await message.reply_text(f"{t('broadcast_done', lang)}\n✅ {result['success']} | ❌ {result['failed']}")
        return

    if action == 'set_card':
        try:
            card, holder = [part.strip() for part in text.split('|', 1)]
        except ValueError:
            await message.reply_text('فرمت نادرست است. مثال: 6037-xxxx | Ali Ahmadi')
            return
        db.set_setting('bank_card_number', card)
        db.set_setting('bank_card_holder', holder)
        settings = context.application.bot_data['config']
        settings.bank_card_number = card
        settings.bank_card_holder = holder
        context.user_data.pop('admin_action', None)
        await message.reply_text('اطلاعات کارت ذخیره شد ✅')
        return

    if action == 'set_limit':
        try:
            limit = int(text.strip())
        except ValueError:
            await message.reply_text('فقط عدد بفرست.')
            return
        db.set_free_daily_limit(limit)
        context.application.bot_data['config'].free_daily_limit = limit
        context.user_data.pop('admin_action', None)
        await message.reply_text('محدودیت روزانه ذخیره شد ✅')
        return

    if action == 'set_free_ad':
        try:
            key, value = [part.strip() for part in text.split('|', 1)]
        except ValueError:
            await message.reply_text('فرمت باید این باشد: interval | 3 یا fa | متن یا en | text')
            return
        if key == 'interval':
            try:
                interval = int(value)
            except ValueError:
                await message.reply_text('برای interval فقط عدد بفرست.')
                return
            db.set_ad_interval(interval)
            context.application.bot_data['config'].free_ad_interval = interval
            context.user_data.pop('admin_action', None)
            await message.reply_text('فاصله نمایش تبلیغ ذخیره شد ✅')
            return
        if key in {'fa', 'en'}:
            db.set_setting(f'free_ad_message_{key}', value)
            context.user_data.pop('admin_action', None)
            await message.reply_text('متن تبلیغ ذخیره شد ✅')
            return
        await message.reply_text('کلید باید interval یا fa یا en باشد.')
        return

    if action == 'manage_sponsors':
        parts = [part.strip() for part in text.split('|')]
        if not parts:
            await message.reply_text('فرمت نادرست است.')
            return
        cmd = parts[0].lower()
        if cmd == 'add' and len(parts) >= 4:
            db.add_sponsor_channel(parts[1], parts[2], parts[3])
            context.user_data.pop('admin_action', None)
            await message.reply_text(t('sponsor_added', lang))
            return
        if cmd == 'remove' and len(parts) >= 2:
            try:
                sponsor_id = int(parts[1])
            except ValueError:
                await message.reply_text('شناسه اسپانسر باید عدد باشد.')
                return
            if db.remove_sponsor(sponsor_id):
                context.user_data.pop('admin_action', None)
                await message.reply_text(t('sponsor_removed', lang))
            else:
                await message.reply_text('شناسه پیدا نشد.')
            return
        await message.reply_text('فرمت صحیح:\nadd | chat_id | title | invite_link\nremove | sponsor_id')
        return

    if action == 'disable_bot':
        db.set_setting('off_message_fa', text)
        db.set_setting('off_message_en', text)
        db.set_bot_enabled(False)
        context.user_data.pop('admin_action', None)
        await message.reply_text(t('bot_disabled_custom', lang))
        return

    if action == 'set_welcome':
        try:
            language, value = [part.strip() for part in text.split('|', 1)]
        except ValueError:
            await message.reply_text('فرمت: fa | متن یا en | text')
            return
        if language not in {'fa', 'en'}:
            await message.reply_text('زبان باید fa یا en باشد.')
            return
        db.set_setting(f'welcome_message_{language}', value)
        context.user_data.pop('admin_action', None)
        await message.reply_text('پیام خوش‌آمد ذخیره شد ✅')
        return

    if action == 'set_system_message':
        try:
            key, value = [part.strip() for part in text.split('|', 1)]
        except ValueError:
            await message.reply_text('فرمت: key | value')
            return
        db.set_setting(key, value)
        context.user_data.pop('admin_action', None)
        await message.reply_text('پیام سیستمی ذخیره شد ✅')
        return


@admin_required
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    db = context.application.bot_data['db']
    stats = db.stats()
    platform_lines = '\n'.join(f'• {k}: {v}' for k, v in stats['platform_stats'].items()) or '-'
    text = (
        f"📊 آمار ربات\n\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"🔥 کاربران فعال: {stats['active_users']}\n"
        f"🆕 کاربران جدید امروز: {stats['new_today']}\n"
        f"🎵 تعداد تشخیص آهنگ: {stats['recognition_count']}\n"
        f"💰 درآمد: {stats['income']:,} تومان\n\n"
        f"دانلودها بر اساس پلتفرم:\n{platform_lines}"
    )
    await message.reply_text(text)


@admin_required
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text('Usage: /ban user_id')
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await message.reply_text('user_id must be integer')
        return
    db = context.application.bot_data['db']
    if db.ban_user(user_id, True):
        await message.reply_text('کاربر بن شد ✅')
    else:
        await message.reply_text('کاربر پیدا نشد.')


@admin_required
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text('Usage: /unban user_id')
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await message.reply_text('user_id must be integer')
        return
    db = context.application.bot_data['db']
    if db.ban_user(user_id, False):
        await message.reply_text('کاربر آنبن شد ✅')
    else:
        await message.reply_text('کاربر پیدا نشد.')


@admin_required
async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if len(context.args) < 2:
        await message.reply_text('Usage: /vip user_id days')
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await message.reply_text('Arguments must be integers')
        return
    db = context.application.bot_data['db']
    if db.give_vip(user_id, days):
        await message.reply_text(f'اشتراک VIP به مدت {days} روز فعال شد ✅')
        try:
            await context.bot.send_message(user_id, 'اشتراک VIP شما توسط ادمین فعال شد ✅')
        except Exception:
            pass
    else:
        await message.reply_text('کاربر پیدا نشد.')


@admin_required
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    queue_service = context.application.bot_data['queue_service']
    report = build_startup_report(settings, db, queue_service.stats())
    await message.reply_text(report, disable_web_page_preview=True)


@admin_required
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_stats(update, context)
