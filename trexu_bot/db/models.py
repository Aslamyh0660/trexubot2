from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default='fa')
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    vip_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    vip_expiry_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    referral_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    referred_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_download_credits: Mapped[int] = mapped_column(Integer, default=0)
    daily_downloads: Mapped[int] = mapped_column(Integer, default=0)
    daily_reset_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    downloads = relationship('DownloadHistory', back_populates='user')
    recognitions = relationship('MusicRecognition', back_populates='user')
    playlist_items = relationship('PlaylistItem', back_populates='user')
    payments = relationship('PaymentRequest', back_populates='user')


class SponsorChannel(Base):
    __tablename__ = 'sponsor_channels'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    invite_link: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BotSetting(Base):
    __tablename__ = 'bot_settings'

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class DownloadHistory(Base):
    __tablename__ = 'download_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    source_url: Mapped[str] = mapped_column(String(1000), index=True)
    platform: Mapped[str] = mapped_column(String(100), default='unknown')
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000))
    file_kind: Mapped[str] = mapped_column(String(50))
    format_code: Mapped[str] = mapped_column(String(50), default='default')
    telegram_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='downloads')


class MusicRecognition(Base):
    __tablename__ = 'music_recognition'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='recognitions')


class PlaylistItem(Base):
    __tablename__ = 'playlist_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(255))
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    artwork_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='playlist_items')


class PaymentRequest(Base):
    __tablename__ = 'payment_requests'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    plan_code: Mapped[str] = mapped_column(String(50))
    amount: Mapped[int] = mapped_column(Integer)
    receipt_file_id: Mapped[str] = mapped_column(String(255))
    receipt_type: Mapped[str] = mapped_column(String(50), default='photo')
    status: Mapped[str] = mapped_column(String(50), default='pending', index=True)
    admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='payments')
