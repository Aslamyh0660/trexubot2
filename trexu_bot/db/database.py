from __future__ import annotations

import json
import logging
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Generator, Iterable

from sqlalchemy import create_engine, desc, func, select
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, BotSetting, DownloadHistory, MusicRecognition, PaymentRequest, PlaylistItem, SponsorChannel, User

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, database_url: str, admin_ids: Iterable[int] | None = None, default_lang: str = 'fa') -> None:
        connect_args = {'check_same_thread': False} if database_url.startswith('sqlite') else {}
        self.engine = create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self.admin_ids = set(admin_ids or [])
        self.default_lang = default_lang

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.session_scope() as session:
            self._ensure_setting(session, 'bot_enabled', '1')
            self._ensure_setting(session, 'off_message_fa', 'ربات موقتاً غیرفعال است.')
            self._ensure_setting(session, 'off_message_en', 'Bot is temporarily disabled.')
            self._ensure_setting(session, 'welcome_message_fa', 'سلام! به Trexu Bot خوش آمدی.')
            self._ensure_setting(session, 'welcome_message_en', 'Hello! Welcome to Trexu Bot.')
            self._ensure_setting(session, 'free_daily_limit', '5')
            self._ensure_setting(session, 'free_ad_interval', '3')
            self._ensure_setting(session, 'free_ad_message_fa', '📢 حمایت از Trexu Bot\n\nبرای حذف تبلیغ، دانلود نامحدود و کیفیت 1080p از بخش VIP استفاده کن.')
            self._ensure_setting(session, 'free_ad_message_en', '📢 Support Trexu Bot\n\nUpgrade to VIP for ad-free unlimited downloads and 1080p quality.')

    def _ensure_setting(self, session: Session, key: str, value: str) -> None:
        if not session.get(BotSetting, key):
            session.add(BotSetting(key=key, value=value))

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception('Database transaction failed')
            raise
        finally:
            session.close()

    def get_or_create_user(self, tg_id: int, username: str | None, first_name: str | None, lang: str | None = None) -> User:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if user:
                user.username = username
                user.first_name = first_name
                user.last_active_at = datetime.utcnow()
                if tg_id in self.admin_ids:
                    user.is_admin = True
                return user
            user = User(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                language=lang or self.default_lang,
                is_admin=tg_id in self.admin_ids,
                referral_code=secrets.token_urlsafe(6).replace('-', '').replace('_', '')[:10],
                created_at=datetime.utcnow(),
                last_active_at=datetime.utcnow(),
                daily_reset_at=datetime.utcnow(),
            )
            session.add(user)
            session.flush()
            return user

    def get_user(self, tg_id: int) -> User | None:
        with self.session_scope() as session:
            return session.scalar(select(User).where(User.tg_id == tg_id))

    def get_user_lang(self, tg_id: int) -> str:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            return user.language if user else self.default_lang

    def set_user_lang(self, tg_id: int, lang: str) -> None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if user:
                user.language = lang
                user.last_active_at = datetime.utcnow()

    def process_referral(self, user_tg_id: int, ref_code: str) -> bool:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == user_tg_id))
            inviter = session.scalar(select(User).where(User.referral_code == ref_code))
            if not user or not inviter or inviter.tg_id == user_tg_id or user.referred_by:
                return False
            user.referred_by = inviter.tg_id
            inviter.referrals_count += 1
            inviter.extra_download_credits += 3
            return True

    def is_admin(self, tg_id: int) -> bool:
        if tg_id in self.admin_ids:
            return True
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            return bool(user and user.is_admin)

    def is_banned(self, tg_id: int) -> bool:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            return bool(user and user.is_banned)

    def ban_user(self, tg_id: int, banned: bool = True) -> bool:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return False
            user.is_banned = banned
            return True

    def give_vip(self, tg_id: int, days: int) -> bool:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return False
            base = user.vip_until if user.vip_until and user.vip_until > datetime.utcnow() else datetime.utcnow()
            user.is_vip = True
            user.vip_until = base + timedelta(days=days)
            user.vip_expiry_notified_at = None
            return True

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.session_scope() as session:
            row = session.get(BotSetting, key)
            return row.value if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.session_scope() as session:
            row = session.get(BotSetting, key)
            if row:
                row.value = value
            else:
                session.add(BotSetting(key=key, value=value))

    def bot_enabled(self) -> bool:
        return (self.get_setting('bot_enabled', '1') or '1') == '1'

    def set_bot_enabled(self, enabled: bool) -> None:
        self.set_setting('bot_enabled', '1' if enabled else '0')

    def get_free_daily_limit(self, default: int) -> int:
        value = self.get_setting('free_daily_limit', str(default))
        try:
            return int(value or default)
        except ValueError:
            return default

    def set_free_daily_limit(self, limit: int) -> None:
        self.set_setting('free_daily_limit', str(limit))

    def get_ad_interval(self, default: int) -> int:
        value = self.get_setting('free_ad_interval', str(default))
        try:
            return int(value or default)
        except ValueError:
            return default

    def set_ad_interval(self, interval: int) -> None:
        self.set_setting('free_ad_interval', str(interval))

    def _refresh_user_daily_limit(self, user: User) -> None:
        now = datetime.utcnow()
        if not user.daily_reset_at or user.daily_reset_at.date() != now.date():
            user.daily_downloads = 0
            user.daily_reset_at = now

        if user.vip_until and user.vip_until < now:
            user.is_vip = False

    def can_user_download(self, tg_id: int, free_daily_limit: int) -> tuple[bool, str | None]:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return False, 'user_not_found'
            self._refresh_user_daily_limit(user)
            if user.is_banned:
                return False, 'banned'
            if user.is_vip and user.vip_until and user.vip_until > datetime.utcnow():
                return True, None
            if user.daily_downloads < free_daily_limit:
                return True, None
            if user.extra_download_credits > 0:
                return True, 'credit'
            return False, 'daily_limit'

    def register_download_usage(self, tg_id: int, free_daily_limit: int) -> None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return
            self._refresh_user_daily_limit(user)
            if user.is_vip and user.vip_until and user.vip_until > datetime.utcnow():
                return
            if user.daily_downloads < free_daily_limit:
                user.daily_downloads += 1
            elif user.extra_download_credits > 0:
                user.extra_download_credits -= 1

    def add_sponsor_channel(self, chat_id: str, title: str, invite_link: str) -> SponsorChannel:
        with self.session_scope() as session:
            row = session.scalar(select(SponsorChannel).where(SponsorChannel.chat_id == chat_id))
            if row:
                row.title = title
                row.invite_link = invite_link
                row.is_active = True
                return row
            row = SponsorChannel(chat_id=chat_id, title=title, invite_link=invite_link, is_active=True)
            session.add(row)
            session.flush()
            return row

    def list_sponsors(self, active_only: bool = True) -> list[SponsorChannel]:
        with self.session_scope() as session:
            stmt = select(SponsorChannel)
            if active_only:
                stmt = stmt.where(SponsorChannel.is_active.is_(True))
            return list(session.scalars(stmt.order_by(SponsorChannel.id)).all())

    def remove_sponsor(self, sponsor_id: int) -> bool:
        with self.session_scope() as session:
            row = session.get(SponsorChannel, sponsor_id)
            if not row:
                return False
            session.delete(row)
            return True

    def save_recognition(self, user_tg_id: int, artist: str | None, title: str | None, album: str | None, cover_url: str | None, external_url: str | None, source_file_id: str | None) -> None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == user_tg_id))
            if not user:
                return
            session.add(
                MusicRecognition(
                    user_id=user.id,
                    artist=artist,
                    title=title,
                    album=album,
                    cover_url=cover_url,
                    external_url=external_url,
                    source_file_id=source_file_id,
                )
            )

    def find_cached_download(self, source_url: str, file_kind: str, format_code: str) -> DownloadHistory | None:
        with self.session_scope() as session:
            item = session.scalar(
                select(DownloadHistory)
                .where(
                    DownloadHistory.source_url == source_url,
                    DownloadHistory.file_kind == file_kind,
                    DownloadHistory.format_code == format_code,
                )
                .order_by(desc(DownloadHistory.created_at))
            )
            return item

    def save_download_record(
        self,
        user_tg_id: int,
        source_url: str,
        platform: str,
        title: str | None,
        artist: str | None,
        file_path: str,
        file_kind: str,
        format_code: str,
        telegram_file_id: str | None = None,
    ) -> DownloadHistory:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == user_tg_id))
            if not user:
                raise ValueError('User not found')
            row = DownloadHistory(
                user_id=user.id,
                source_url=source_url,
                platform=platform,
                title=title,
                artist=artist,
                file_path=file_path,
                file_kind=file_kind,
                format_code=format_code,
                telegram_file_id=telegram_file_id,
            )
            session.add(row)
            session.flush()
            return row

    def recent_history(self, tg_id: int, limit: int = 10) -> list[DownloadHistory]:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return []
            return list(
                session.scalars(
                    select(DownloadHistory)
                    .where(DownloadHistory.user_id == user.id)
                    .order_by(desc(DownloadHistory.created_at))
                    .limit(limit)
                ).all()
            )

    def count_user_downloads(self, tg_id: int) -> int:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return 0
            value = session.scalar(select(func.count(DownloadHistory.id)).where(DownloadHistory.user_id == user.id)) or 0
            return int(value)

    def add_playlist_item(self, tg_id: int, title: str, artist: str | None, source_url: str | None, artwork_url: str | None) -> PlaylistItem | None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return None
            row = PlaylistItem(user_id=user.id, title=title, artist=artist, source_url=source_url, artwork_url=artwork_url)
            session.add(row)
            session.flush()
            return row

    def list_playlist(self, tg_id: int, limit: int = 20) -> list[PlaylistItem]:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return []
            return list(
                session.scalars(
                    select(PlaylistItem)
                    .where(PlaylistItem.user_id == user.id)
                    .order_by(desc(PlaylistItem.created_at))
                    .limit(limit)
                ).all()
            )

    def create_payment_request(self, tg_id: int, plan_code: str, amount: int, receipt_file_id: str, receipt_type: str) -> PaymentRequest | None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return None
            row = PaymentRequest(
                user_id=user.id,
                plan_code=plan_code,
                amount=amount,
                receipt_file_id=receipt_file_id,
                receipt_type=receipt_type,
                status='pending',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            return row

    def get_pending_payments(self) -> list[PaymentRequest]:
        with self.session_scope() as session:
            return list(session.scalars(select(PaymentRequest).where(PaymentRequest.status == 'pending').order_by(PaymentRequest.created_at)).all())

    def get_payment(self, payment_id: int) -> PaymentRequest | None:
        with self.session_scope() as session:
            return session.get(PaymentRequest, payment_id)

    def approve_payment(self, payment_id: int, admin_id: int, days: int) -> PaymentRequest | None:
        with self.session_scope() as session:
            payment = session.get(PaymentRequest, payment_id)
            if not payment or payment.status != 'pending':
                return None
            payment.status = 'approved'
            payment.admin_id = admin_id
            payment.updated_at = datetime.utcnow()
            user = session.get(User, payment.user_id)
            if not user:
                return None
            base = user.vip_until if user.vip_until and user.vip_until > datetime.utcnow() else datetime.utcnow()
            user.is_vip = True
            user.vip_until = base + timedelta(days=days)
            user.vip_expiry_notified_at = None
            session.flush()
            return payment

    def reject_payment(self, payment_id: int, admin_id: int, note: str | None = None) -> PaymentRequest | None:
        with self.session_scope() as session:
            payment = session.get(PaymentRequest, payment_id)
            if not payment or payment.status != 'pending':
                return None
            payment.status = 'rejected'
            payment.admin_id = admin_id
            payment.note = note
            payment.updated_at = datetime.utcnow()
            return payment

    def get_user_by_payment(self, payment_id: int) -> User | None:
        with self.session_scope() as session:
            payment = session.get(PaymentRequest, payment_id)
            if not payment:
                return None
            return session.get(User, payment.user_id)

    def stats(self) -> dict[str, object]:
        with self.session_scope() as session:
            today = datetime.utcnow().date()
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            total_users = session.scalar(select(func.count(User.id))) or 0
            active_users = session.scalar(select(func.count(User.id)).where(User.last_active_at >= seven_days_ago)) or 0
            new_today = session.scalar(select(func.count(User.id)).where(func.date(User.created_at) == str(today))) or 0
            recognition_count = session.scalar(select(func.count(MusicRecognition.id))) or 0
            income = session.scalar(select(func.sum(PaymentRequest.amount)).where(PaymentRequest.status == 'approved')) or 0
            platform_rows = session.execute(
                select(DownloadHistory.platform, func.count(DownloadHistory.id)).group_by(DownloadHistory.platform)
            ).all()
            return {
                'total_users': int(total_users),
                'active_users': int(active_users),
                'new_today': int(new_today),
                'recognition_count': int(recognition_count),
                'income': int(income),
                'platform_stats': {platform: count for platform, count in platform_rows},
            }

    def list_user_ids(self) -> list[int]:
        with self.session_scope() as session:
            return [row[0] for row in session.execute(select(User.tg_id)).all()]

    def get_account_snapshot(self, tg_id: int) -> dict[str, object] | None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if not user:
                return None
            self._refresh_user_daily_limit(user)
            return {
                'tg_id': user.tg_id,
                'username': user.username,
                'first_name': user.first_name,
                'language': user.language,
                'is_vip': user.is_vip and bool(user.vip_until and user.vip_until > datetime.utcnow()),
                'vip_until': user.vip_until,
                'daily_downloads': user.daily_downloads,
                'referral_code': user.referral_code,
                'referrals_count': user.referrals_count,
                'extra_download_credits': user.extra_download_credits,
                'created_at': user.created_at,
            }

    def expiring_vips(self, within_days: int = 3) -> list[User]:
        with self.session_scope() as session:
            now = datetime.utcnow()
            until = now + timedelta(days=within_days)
            stmt = select(User).where(
                User.is_vip.is_(True),
                User.vip_until.is_not(None),
                User.vip_until <= until,
                User.vip_until >= now,
            )
            return list(session.scalars(stmt).all())

    def mark_expiry_notified(self, tg_id: int) -> None:
        with self.session_scope() as session:
            user = session.scalar(select(User).where(User.tg_id == tg_id))
            if user:
                user.vip_expiry_notified_at = datetime.utcnow()

    def settings_dump(self) -> dict[str, str]:
        with self.session_scope() as session:
            rows = session.scalars(select(BotSetting)).all()
            return {row.key: row.value for row in rows}

    def export_summary_json(self) -> str:
        return json.dumps(self.stats(), ensure_ascii=False, indent=2)
