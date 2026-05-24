from datetime import datetime, timezone
from sqlalchemy import BigInteger, String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class User(Base):
    __tablename__ = "users"

    # Уникальный внутренний ID записи в нашей БД
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Telegram ID пользователя (может быть пустым, если человек зарегистрировался только на сайте)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)

    # Username пользователя (используется как логин на сайте и как уникальный Email в панели 3x-ui)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Email пользователя (используется как логин на сайте)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Хэш пароля для авторизации на сайте
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Уникальный UUID-пароль из 3x-ui
    vpn_uuid: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)

    # Секретный 16-значный subId подписки из 3x-ui
    vpn_sub_id: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)

    # Текущее название инбаунда
    vpn_inbound_remark: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Дата окончания действия VPN подписки
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Дата регистрации аккаунта в системе
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}' username='{self.username}'>"
