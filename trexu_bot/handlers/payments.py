from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from ..i18n import t
from ..keyboards.inline import payment_review_keyboard


async def prompt_payment_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE, plan_code: str) -> None:
    user = update.effective_user
    target = update.effective_message if update.effective_message else update.callback_query.message
    if not user or not target:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    lang = db.get_user_lang(user.id)
    plan = settings.vip_plans.get(plan_code)
    if not plan:
        return

    context.user_data['pending_payment_plan'] = plan_code
    title = plan.title_fa if lang == 'fa' else plan.title_en
    text = t(
        'payment_details',
        lang,
        plan=title,
        amount=plan.price,
        card=settings.bank_card_number,
        holder=settings.bank_card_holder,
    )
    await target.reply_text(text, parse_mode='Markdown')
    await target.reply_text(t('send_receipt', lang))


async def handle_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return

    plan_code = context.user_data.get('pending_payment_plan')
    if not plan_code:
        return

    db = context.application.bot_data['db']
    settings = context.application.bot_data['config']
    lang = db.get_user_lang(user.id)
    plan = settings.vip_plans.get(plan_code)
    if not plan:
        return

    receipt_file_id = None
    receipt_type = None
    if message.photo:
        receipt_file_id = message.photo[-1].file_id
        receipt_type = 'photo'
    elif message.document:
        receipt_file_id = message.document.file_id
        receipt_type = 'document'

    if not receipt_file_id or not receipt_type:
        return

    payment = db.create_payment_request(user.id, plan_code, plan.price, receipt_file_id, receipt_type)
    if not payment:
        return

    context.user_data.pop('pending_payment_plan', None)
    await message.reply_text(t('payment_submitted', lang))

    caption = (
        f'🧾 درخواست پرداخت جدید\n\n'
        f'Payment ID: {payment.id}\n'
        f'User ID: {user.id}\n'
        f'Username: @{user.username or "-"}\n'
        f'Plan: {plan.title_fa}\n'
        f'Amount: {plan.price:,} Toman'
    )
    for admin_id in settings.admin_ids:
        if receipt_type == 'photo':
            await context.bot.send_photo(admin_id, receipt_file_id, caption=caption, reply_markup=payment_review_keyboard(payment.id))
        else:
            await context.bot.send_document(admin_id, receipt_file_id, caption=caption, reply_markup=payment_review_keyboard(payment.id))
