from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from telegram import Bot

from .helpers import human_size, progress_bar


@dataclass(slots=True)
class ProgressContext:
    bot: Bot
    loop: asyncio.AbstractEventLoop
    chat_id: int
    message_id: int
    title: str
    last_edit_ts: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, text: str) -> None:
        async def _edit() -> None:
            try:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    text=text,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

        asyncio.run_coroutine_threadsafe(_edit(), self.loop)

    def hook(self, data: dict[str, Any]) -> None:
        status = data.get('status')
        with self.lock:
            now = time.time()
            if status == 'downloading':
                if now - self.last_edit_ts < 1.6:
                    return
                total = data.get('total_bytes') or data.get('total_bytes_estimate') or 0
                downloaded = data.get('downloaded_bytes') or 0
                percent = (downloaded / total * 100) if total else 0
                speed = human_size(int(data.get('speed') or 0))
                eta = int(data.get('eta') or 0)
                bar = progress_bar(percent)
                text = (
                    f'⬇️ {self.title}\n'
                    f'{bar} {percent:.1f}%\n'
                    f'حجم: {human_size(downloaded)} / {human_size(total)}\n'
                    f'سرعت: {speed}/s | ETA: {eta}s'
                )
                self.emit(text)
                self.last_edit_ts = now
            elif status == 'finished':
                self.emit(f'⚙️ {self.title}\nدانلود تمام شد، در حال پردازش فایل...')
                self.last_edit_ts = now
