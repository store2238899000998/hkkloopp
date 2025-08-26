from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, BigInteger, String  # BigInteger added
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
	__tablename__ = "users"

	user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Fixed
	name: Mapped[str] = mapped_column(String(120), nullable=False)
	email: Mapped[str | None] = mapped_column(String(120), nullable=True)
	phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
	country: Mapped[str | None] = mapped_column(String(60), nullable=True)
	initial_balance: Mapped[float] = mapped_column(Float, default=0.0)
	current_balance: Mapped[float] = mapped_column(Float, default=0.0)
	start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
	next_roi_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
	roi_cycles_completed: Mapped[int] = mapped_column(BigInteger, default=0)  # Optional: safer to use BigInteger here too
	can_withdraw: Mapped[bool] = mapped_column(Boolean, default=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
	updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupportTicket(Base):
	__tablename__ = "support_tickets"

	ticket_id: Mapped[str] = mapped_column(String(36), primary_key=True)
	user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # Fixed
	message: Mapped[str] = mapped_column(String(2048), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccessCode(Base):
	__tablename__ = "access_codes"

	code: Mapped[str] = mapped_column(String(32), primary_key=True)
	name: Mapped[str] = mapped_column(String(120), nullable=False)
	initial_balance: Mapped[float] = mapped_column(Float, default=0.0)
	preassigned_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Fixed
	expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
	used_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # Fixed
	used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
	created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

