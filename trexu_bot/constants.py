from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DOWNLOAD_DIR = DATA_DIR / 'downloads'
TEMP_DIR = DATA_DIR / 'temp'
LOG_DIR = DATA_DIR / 'logs'

DEFAULT_WELCOME_FA = (
    'سلام 👋\n\n'
    'به Trexu Bot خوش اومدی.\n'
    'از منوی پایین می‌تونی آهنگ پیدا کنی، لینک دانلود کنی و اشتراک VIP بگیری.'
)

DEFAULT_WELCOME_EN = (
    'Hello 👋\n\n'
    'Welcome to Trexu Bot.\n'
    'Use the menu below to search music, download media, and manage VIP plans.'
)

DEFAULT_OFF_MESSAGE_FA = 'ربات موقتاً غیرفعال است. لطفاً کمی بعد دوباره تلاش کنید.'
DEFAULT_OFF_MESSAGE_EN = 'Bot is temporarily disabled. Please try again later.'

SUPPORTED_LANGS = ('fa', 'en')

FREE_PLAN_CODE = 'free'
VIP_PLAN_CODES = ('vip_1m', 'vip_3m', 'vip_12m')

CACHE_KINDS = ('video_360', 'video_720', 'video_1080', 'audio_mp3', 'music_detect')
