from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, BigInteger, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    initial_balance: Mapped[float] = mapped_column(Float, default=0.0)
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)
    roi_cycles_completed: Mapped[int] = mapped_column(BigInteger, default=0)
    max_roi_cycles: Mapped[int] = mapped_column(BigInteger, default=4)
    next_roi_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    can_withdraw: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    support_tickets: Mapped[list["SupportTicket"]] = relationship(back_populates="user")
    investment_history: Mapped[list["InvestmentHistory"]] = relationship(back_populates="user")


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, closed, in_progress
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="support_tickets")


class AccessCode(Base):
    __tablename__ = "access_codes"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    preassigned_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class InvestmentHistory(Base):
    __tablename__ = "investment_history"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # roi_payment, reinvestment, withdrawal, initial_deposit, admin_credit
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance_before: Mapped[float] = mapped_column(Float, nullable=False)
    balance_after: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for additional data
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="investment_history")

