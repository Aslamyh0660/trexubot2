from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .constants import BASE_DIR, DOWNLOAD_DIR, TEMP_DIR


load_dotenv(BASE_DIR / '.env')


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


@dataclass(slots=True)
class VIPPlan:
    code: str
    title_fa: str
    title_en: str
    price: int
    days: int


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    database_url: str
    audd_api_token: str | None
    genius_api_token: str | None
    channel_url: str
    support_username: str
    bank_card_number: str
    bank_card_holder: str
    free_daily_limit: int
    force_join_skip_admins: bool
    max_file_age_days: int
    request_timeout: int
    download_workers: int
    free_ad_interval: int
    bot_name: str
    default_lang: str
    base_dir: Path = field(default=BASE_DIR)
    download_dir: Path = field(default=DOWNLOAD_DIR)
    temp_dir: Path = field(default=TEMP_DIR)
    yt_dlp_cookie_file: str | None = None
    proxy_url: str | None = None
    vip_plans: dict[str, VIPPlan] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> 'Settings':
        bot_token = os.getenv('BOT_TOKEN', '').strip()
        if not bot_token:
            raise ValueError('BOT_TOKEN is required')

        admin_ids_raw = os.getenv('ADMIN_IDS', '').strip()
        admin_ids = [int(item.strip()) for item in admin_ids_raw.split(',') if item.strip()]

        download_dir = Path(os.getenv('DOWNLOAD_DIR', str(DOWNLOAD_DIR))).expanduser().resolve()
        temp_dir = Path(os.getenv('TEMP_DIR', str(TEMP_DIR))).expanduser().resolve()

        settings = cls(
            bot_token=bot_token,
            admin_ids=admin_ids,
            database_url=os.getenv('DATABASE_URL', f"sqlite:///{(BASE_DIR / 'trexu.db').as_posix()}"),
            audd_api_token=os.getenv('AUDD_API_TOKEN') or None,
            genius_api_token=os.getenv('GENIUS_API_TOKEN') or None,
            channel_url=os.getenv('CHANNEL_URL', 'https://t.me/your_channel'),
            support_username=os.getenv('SUPPORT_USERNAME', '@your_support'),
            bank_card_number=os.getenv('BANK_CARD_NUMBER', '0000-0000-0000-0000'),
            bank_card_holder=os.getenv('BANK_CARD_HOLDER', 'TREXU BOT'),
            free_daily_limit=_to_int(os.getenv('FREE_DAILY_LIMIT'), 5),
            force_join_skip_admins=_to_bool(os.getenv('FORCE_JOIN_SKIP_ADMINS'), True),
            max_file_age_days=_to_int(os.getenv('MAX_FILE_AGE_DAYS'), 2),
            request_timeout=_to_int(os.getenv('REQUEST_TIMEOUT'), 120),
            download_workers=_to_int(os.getenv('DOWNLOAD_WORKERS'), 2),
            free_ad_interval=_to_int(os.getenv('FREE_AD_INTERVAL'), 3),
            bot_name=os.getenv('BOT_NAME', 'Trexu Bot'),
            default_lang=os.getenv('DEFAULT_LANG', 'fa').strip().lower() or 'fa',
            download_dir=download_dir,
            temp_dir=temp_dir,
            yt_dlp_cookie_file=os.getenv('YT_DLP_COOKIE_FILE') or None,
            proxy_url=os.getenv('PROXY_URL') or None,
        )
        settings.vip_plans = settings._load_vip_plans()
        return settings

    def _load_vip_plans(self) -> dict[str, VIPPlan]:
        return {
            'vip_1m': VIPPlan(
                code='vip_1m',
                title_fa='VIP یک‌ماهه',
                title_en='VIP 1 Month',
                price=_to_int(os.getenv('VIP_1M_PRICE'), 199000),
                days=30,
            ),
            'vip_3m': VIPPlan(
                code='vip_3m',
                title_fa='VIP سه‌ماهه',
                title_en='VIP 3 Months',
                price=_to_int(os.getenv('VIP_3M_PRICE'), 499000),
                days=90,
            ),
            'vip_12m': VIPPlan(
                code='vip_12m',
                title_fa='VIP یک‌ساله',
                title_en='VIP 12 Months',
                price=_to_int(os.getenv('VIP_12M_PRICE'), 1599000),
                days=365,
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            'bot_name': self.bot_name,
            'free_daily_limit': self.free_daily_limit,
            'default_lang': self.default_lang,
            'channel_url': self.channel_url,
            'support_username': self.support_username,
            'max_file_age_days': self.max_file_age_days,
            'download_workers': self.download_workers,
            'free_ad_interval': self.free_ad_interval,
        }
