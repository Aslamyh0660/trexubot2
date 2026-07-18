from __future__ import annotations

import asyncio
import logging

from telegram import Bot

logger = logging.getLogger(__name__)


async def broadcast_copy(bot: Bot, user_ids: list[int], from_chat_id: int, message_id: int) -> dict[str, int]:
    success = 0
    failed = 0
    for user_id in user_ids:
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=from_chat_id, message_id=message_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            logger.exception('Broadcast failed for user %s', user_id)
    return {'success': success, 'failed': failed}
