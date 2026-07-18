# Trexu Bot 🎵

ربات چندمنظوره تلگرام برای **تشخیص آهنگ، جست‌وجو و دانلود موسیقی** با معماری ماژولار و آماده‌ی اجرا روی سرور، Docker و Termux.

## قابلیت‌ها

- تشخیص آهنگ با AudD
- جست‌وجو و دریافت اطلاعات آهنگ از سرویس‌های موسیقی
- دانلودر چندمنظوره با `yt-dlp`
- صف دانلود با اولویت کاربران VIP
- سیستم VIP، پرداخت دستی و ارجاع دوستان
- Force Join چندکاناله
- پنل مدیریت و گزارش سلامت ربات
- تاریخچه دانلود و پشتیبانی از زبان فارسی و انگلیسی
- پاک‌سازی خودکار فایل‌های موقت
- پشتیبانی از SQLite برای اجرای ساده و PostgreSQL برای محیط production

## ساختار پروژه

```text
.
├── bot2.py                 # نقطه ورود برنامه
├── trexu_bot/              # کد اصلی برنامه
│   ├── handlers/           # مدیریت پیام‌ها و رویدادهای تلگرام
│   ├── services/           # منطق سرویس‌ها و دانلود
│   ├── db/                 # مدل‌ها و اتصال دیتابیس
│   ├── keyboards/          # کیبوردهای Reply و Inline
│   └── utils/              # ابزارهای کمکی
├── data/                   # داده‌های runtime (در Git نادیده گرفته می‌شود)
├── .env.example            # الگوی متغیرهای محیطی
├── Dockerfile
└── requirements.txt
```

## اجرای محلی

> Python 3.11 یا بالاتر و `ffmpeg` لازم است.

```bash
git clone https://github.com/Aslamyh0660/trexubot2.git
cd trexubot2
python -m venv .venv
source .venv/bin/activate  # در ویندوز: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# فایل .env را با مقادیر واقعی تکمیل کنید
python bot2.py
```

## تنظیمات

هرگز فایل `.env` یا توکن‌های واقعی را commit نکنید. متغیرهای اصلی:

- `BOT_TOKEN` و `ADMIN_IDS`
- `DATABASE_URL`
- `AUDD_API_TOKEN` و `GENIUS_API_TOKEN`
- `CHANNEL_URL` و `SUPPORT_USERNAME`
- تنظیمات VIP، صف دانلود و مسیر فایل‌ها

فهرست کامل در [`.env.example`](.env.example) قرار دارد.

## Docker

```bash
docker build -t trexu-bot .
docker run --env-file .env trexu-bot
```

## استقرار

راهنماهای آماده:

- [استقرار روی سرویس‌های ابری](DEPLOY.md)
- [راه‌اندازی در Termux](TERMUX.md)
- [برنامه بازاریابی](MARKETING_PLAN.md)

## ملاحظات امنیتی و حقوقی

- کلیدها و توکن‌ها را فقط در Secret/Environment Variables سرویس استقرار نگه دارید.
- استفاده از قابلیت دانلود باید مطابق قوانین سرویس‌های منبع و قوانین کپی‌رایت محل استفاده باشد.
- برای محیط production، استفاده از PostgreSQL و فضای ذخیره‌سازی پایدار توصیه می‌شود.

## مجوز

مجوز پروژه هنوز تعیین نشده است. پیش از استفاده تجاری یا بازتوزیع، مجوز مناسب به مخزن اضافه کنید.
