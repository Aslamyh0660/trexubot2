# Trexu Bot 🎵

A modular Telegram music bot for song recognition, music search, and media downloads. Built with Python and designed for local development, Docker, and Termux deployments.

## Highlights

- Song recognition powered by AudD
- Music search and metadata retrieval
- Multi-purpose downloading with `yt-dlp`
- Download queue with VIP priority support
- VIP, manual payment, and referral features
- Multi-channel force-join support
- Admin dashboard and bot health reporting
- Download history with Persian and English support
- Automatic cleanup of temporary files
- SQLite for simple deployments and PostgreSQL for production environments

## Project Structure

```text
.
├── bot2.py                 # Application entry point
├── trexu_bot/              # Core application code
│   ├── handlers/           # Telegram events and message handlers
│   ├── services/           # Service integrations and download logic
│   ├── db/                 # Database models and connections
│   ├── keyboards/          # Reply and inline keyboards
│   └── utils/              # Shared utilities
├── data/                   # Runtime data (ignored by Git)
├── .env.example            # Environment variable template
├── Dockerfile
└── requirements.txt
```

## Getting Started

> Requires Python 3.11+ and `ffmpeg`.

```bash
git clone https://github.com/Aslamyh0660/trexubot2.git
cd trexubot2
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Add your values to .env
python bot2.py
```

## Configuration

Never commit `.env` files, API keys, or bot tokens. Main configuration areas include:

- `BOT_TOKEN` and `ADMIN_IDS`
- `DATABASE_URL`
- `AUDD_API_TOKEN` and `GENIUS_API_TOKEN`
- `CHANNEL_URL` and `SUPPORT_USERNAME`
- VIP, queue, and storage settings

See [`.env.example`](.env.example) for the complete configuration template.

## Docker

```bash
docker build -t trexu-bot .
docker run --env-file .env trexu-bot
```

## Deployment Guides

- [Cloud deployment](DEPLOY.md)
- [Termux setup](TERMUX.md)
- [Marketing plan](MARKETING_PLAN.md)

## Security and Responsible Use

- Store secrets only in environment variables or your deployment platform's secret manager.
- Use downloading features in accordance with the source services' terms and applicable copyright laws.
- PostgreSQL and persistent storage are recommended for production deployments.

## License

A license has not been selected yet. Add an appropriate license before commercial use or redistribution.
