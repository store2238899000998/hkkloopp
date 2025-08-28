from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Iterable
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, SupportTicket, AccessCode

# Set up logging
logger = logging.getLogger(__name__)

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
	logger.info(f"✅ Created new user: {name} (ID: {user_id}) with balance: {initial_balance}")
	return user


def create_user_with_access_code(session: Session, name: str, initial_balance: float, email: str | None = None, phone: str | None = None, country: str | None = None) -> tuple[AccessCode, str]:
	"""Create access code for new user registration. Returns (access_code, message)"""
	access = generate_access_code(session, name=name, initial_balance=initial_balance, expires_in_days=30)
	return access, f"✅ User '{name}' registered successfully!\n\n📋 Access Code: `{access.code}`\n💰 Initial Balance: {initial_balance:.2f}\n📧 Email: {email or 'Not provided'}\n📱 Phone: {phone or 'Not provided'}\n🌍 Country: {country or 'Not provided'}\n\nShare this code with the user to activate their account."


def credit_user_balance(session: Session, user_id: int, amount: float) -> Optional[User]:
	user = session.get(User, user_id)
	if not user:
		return None
	old_balance = user.current_balance
	user.current_balance = (user.current_balance or 0.0) + amount
	logger.info(f"💰 Credited user {user_id}: {old_balance:.2f} → {user.current_balance:.2f} (+{amount:.2f})")
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
	logger.info(f"🔑 Generated access code: {code} for {name} (balance: {initial_balance})")
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
	logger.info(f"✅ Access code {code} redeemed by user {user_id}")
	return user


# ROI processing

def process_due_roi_for_user(session: Session, user: User) -> bool:
	"""Process ROI for a single user if they are due"""
	if not user.next_roi_date:
		logger.warning(f"⚠️ User {user.user_id} has no next_roi_date set")
		return False
	
	if datetime.utcnow() < user.next_roi_date:
		return False
	
	if user.roi_cycles_completed >= settings.max_roi_cycles:
		logger.info(f"✅ User {user.user_id} has completed all ROI cycles ({user.roi_cycles_completed}/{settings.max_roi_cycles})")
		return False
	
	# Calculate ROI amount (8% of initial balance)
	roi_amount = (user.initial_balance or 0.0) * (settings.weekly_roi_percent / 100.0)
	old_balance = user.current_balance
	old_cycles = user.roi_cycles_completed
	
	# Apply ROI
	user.current_balance = (user.current_balance or 0.0) + roi_amount
	user.roi_cycles_completed += 1
	
	# Set next ROI date (7 days from the due date, not from now)
	user.next_roi_date = user.next_roi_date + timedelta(days=7)
	
	# Enable withdrawal after 4 cycles
	if user.roi_cycles_completed >= settings.max_roi_cycles:
		user.can_withdraw = True
		logger.info(f"🎯 User {user.user_id} completed all ROI cycles - withdrawal enabled")
	
	logger.info(
		f"💰 ROI processed for user {user.user_id}: "
		f"cycle {old_cycles}→{user.roi_cycles_completed}, "
		f"balance {old_balance:.2f}→{user.current_balance:.2f} "
		f"(+{roi_amount:.2f}), next ROI: {user.next_roi_date.strftime('%Y-%m-%d')}"
	)
	
	return True


def process_weekly_roi(session: Session) -> int:
	"""Process ROI for all users who are due"""
	count = 0
	users = session.execute(select(User)).scalars().all()
	
	logger.info(f"🔄 Processing weekly ROI for {len(users)} users...")
	
	for user in users:
		if process_due_roi_for_user(session, user):
			count += 1
	
	logger.info(f"✅ Weekly ROI processing complete: {count}/{len(users)} users received payments")
	return count


def get_user_roi_status(user: User) -> dict:
	"""Get comprehensive ROI status for a user"""
	now = datetime.utcnow()
	remaining_days = 0
	
	if user.next_roi_date:
		remaining_days = max(0, (user.next_roi_date.date() - now.date()).days)
	
	return {
		"user_id": user.user_id,
		"name": user.name,
		"current_balance": user.current_balance,
		"initial_balance": user.initial_balance,
		"roi_cycles_completed": user.roi_cycles_completed,
		"max_cycles": settings.max_roi_cycles,
		"next_roi_date": user.next_roi_date,
		"remaining_days": remaining_days,
		"can_withdraw": user.can_withdraw,
		"weekly_roi_amount": (user.initial_balance or 0.0) * (settings.weekly_roi_percent / 100.0),
		"total_roi_earned": (user.current_balance or 0.0) - (user.initial_balance or 0.0)
	}


# Support tickets

def create_support_ticket(session: Session, user_id: int, message: str) -> SupportTicket:
	ticket = SupportTicket(
		ticket_id=str(uuid.uuid4()),
		user_id=user_id,
		message=message.strip(),
	)
	session.add(ticket)
	session.flush()
	logger.info(f"🎫 Support ticket created: {ticket.ticket_id} for user {user_id}")
	return ticket


def list_support_tickets(session: Session, limit: int = 50):
	stmt = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
	return session.execute(stmt).scalars().all()


# Withdrawal check (business rule)

def can_withdraw(user: User) -> bool:
	return bool(user.can_withdraw and user.roi_cycles_completed >= settings.max_roi_cycles)
