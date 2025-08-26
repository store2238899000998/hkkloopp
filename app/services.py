from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, SupportTicket, AccessCode


# User management (admin-controlled)

def create_user(session: Session, user_id: int, name: str, initial_balance: float, email: str | None = None, phone: str | None = None, country: str | None = None) -> User:
	user = session.get(User, user_id)
	if user:
		return user
	now = datetime.utcnow()
	user = User(
		user_id=user_id,
		name=name,
		email=email,
		phone=phone,
		country=country,
		initial_balance=initial_balance,
		current_balance=initial_balance,
		start_date=now,
		next_roi_date=now + timedelta(days=7),
		roi_cycles_completed=0,
		can_withdraw=False,
	)
	session.add(user)
	session.flush()
	return user


def create_user_with_access_code(session: Session, name: str, initial_balance: float, email: str | None = None, phone: str | None = None, country: str | None = None) -> tuple[AccessCode, str]:
	"""Create access code for new user registration. Returns (access_code, message)"""
	access = generate_access_code(session, name=name, initial_balance=initial_balance, expires_in_days=30)
	return access, f"✅ User '{name}' registered successfully!\n\n📋 Access Code: `{access.code}`\n💰 Initial Balance: {initial_balance:.2f}\n📧 Email: {email or 'Not provided'}\n📱 Phone: {phone or 'Not provided'}\n🌍 Country: {country or 'Not provided'}\n\nShare this code with the user to activate their account."


def credit_user_balance(session: Session, user_id: int, amount: float) -> Optional[User]:
	user = session.get(User, user_id)
	if not user:
		return None
	user.current_balance = (user.current_balance or 0.0) + amount
	return user


def list_users(session: Session) -> Iterable[User]:
	stmt = select(User)
	return session.execute(stmt).scalars().all()


# Access Code management

def generate_access_code(session: Session, name: str, initial_balance: float, preassigned_user_id: int | None = None, expires_in_days: int | None = 14) -> AccessCode:
	code = secrets.token_hex(4)  # 8 hex chars
	expires_at = None
	if expires_in_days:
		expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
	access = AccessCode(
		code=code,
		name=name,
		initial_balance=initial_balance,
		preassigned_user_id=preassigned_user_id,
		expires_at=expires_at,
	)
	session.add(access)
	session.flush()
	return access


def redeem_access_code(session: Session, code: str, user_id: int) -> Optional[User]:
	access: AccessCode | None = session.get(AccessCode, code)
	if not access:
		return None
	if access.used_by is not None:
		return None
	if access.expires_at and datetime.utcnow() > access.expires_at:
		return None
	if access.preassigned_user_id and access.preassigned_user_id != user_id:
		return None
	user = create_user(session, user_id=user_id, name=access.name, initial_balance=access.initial_balance)
	access.used_by = user_id
	access.used_at = datetime.utcnow()
	return user


# ROI processing

def process_due_roi_for_user(session: Session, user: User) -> bool:
	if not user.next_roi_date or datetime.utcnow() < user.next_roi_date:
		return False
	if user.roi_cycles_completed >= settings.max_roi_cycles:
		return False
	roi_amount = (user.initial_balance or 0.0) * (settings.weekly_roi_percent / 100.0)
	user.current_balance = (user.current_balance or 0.0) + roi_amount
	user.roi_cycles_completed += 1
	user.next_roi_date = user.next_roi_date + timedelta(days=7)
	if user.roi_cycles_completed >= settings.max_roi_cycles:
		user.can_withdraw = True
	return True


def process_weekly_roi(session: Session) -> int:
	count = 0
	users = session.execute(select(User)).scalars().all()
	for user in users:
		if process_due_roi_for_user(session, user):
			count += 1
	return count


# Support tickets

def create_support_ticket(session: Session, user_id: int, message: str) -> SupportTicket:
	ticket = SupportTicket(
		ticket_id=str(uuid.uuid4()),
		user_id=user_id,
		message=message.strip(),
	)
	session.add(ticket)
	session.flush()
	return ticket


def list_support_tickets(session: Session, limit: int = 50):
	stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
	return session.execute(stmt).scalars().all()


# Withdrawal check (business rule)

def can_withdraw(user: User) -> bool:
	return bool(user.can_withdraw and user.roi_cycles_completed >= settings.max_roi_cycles)
