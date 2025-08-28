from __future__ import annotations

import secrets
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Iterable, Tuple, List

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, SupportTicket, AccessCode, InvestmentHistory

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
	
	# Record initial deposit transaction if balance > 0
	if initial_balance > 0:
		try:
			record_investment_transaction(
				session=session,
				user_id=user_id,
				transaction_type="initial_deposit",
				amount=initial_balance,
				balance_before=0.0,
				balance_after=initial_balance,
				description="Initial Investment Deposit",
				metadata={"deposit_type": "initial_registration"}
			)
		except Exception as e:
			logger.error(f"❌ Failed to record initial deposit transaction: {e}")
			# Don't fail user creation for transaction recording issues
	
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
	
	# Record the admin credit transaction
	try:
		record_investment_transaction(
			session=session,
			user_id=user_id,
			transaction_type="admin_credit",
			amount=amount,
			balance_before=old_balance,
			balance_after=user.current_balance,
			description="Admin Credit",
			metadata={"credit_type": "admin_manual"}
		)
	except Exception as e:
		logger.error(f"❌ Failed to record admin credit transaction: {e}")
		# Don't fail credit processing for transaction recording issues
	
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
	
	# Record the ROI transaction
	try:
		record_investment_transaction(
			session=session,
			user_id=user.user_id,
			transaction_type="roi_payment",
			amount=roi_amount,
			balance_before=old_balance,
			balance_after=user.current_balance,
			description=f"ROI Payment - Cycle {user.roi_cycles_completed}",
			metadata={
				"cycle_number": user.roi_cycles_completed,
				"roi_percentage": settings.weekly_roi_percent,
				"base_amount": user.initial_balance
			}
		)
	except Exception as e:
		logger.error(f"❌ Failed to record ROI transaction: {e}")
		# Don't fail ROI processing for transaction recording issues
	
	logger.info(
		f"💰 ROI processed for user {user.user_id}: "
		f"cycle {old_cycles}→{user.roi_cycles_completed}, "
		f"balance {old_balance:.2f}→{user.current_balance:.2f} "
		f"(+{roi_amount:.2f}), next ROI: {user.next_roi_date.strftime('%Y-%m-%d')}"
	)
	
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


def record_investment_transaction(
    session: Session,
    user_id: int,
    transaction_type: str,
    amount: float,
    balance_before: float,
    balance_after: float,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
) -> InvestmentHistory:
    """Record a financial transaction in the investment history"""
    try:
        # Convert metadata to JSON string if provided
        metadata_str = None
        if metadata:
            import json
            metadata_str = json.dumps(metadata)
        
        history_entry = InvestmentHistory(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            transaction_metadata=metadata_str
        )
        
        session.add(history_entry)
        session.commit()
        
        logger.info(f"📊 Recorded {transaction_type} transaction for user {user_id}: ${amount:.2f}")
        return history_entry
        
    except Exception as e:
        logger.error(f"❌ Failed to record investment transaction: {e}")
        session.rollback()
        raise


def get_investment_history(
    session: Session,
    user_id: int,
    limit: int = 50,
    transaction_type: Optional[str] = None
) -> List[InvestmentHistory]:
    """Get investment history for a user with optional filtering"""
    try:
        query = select(InvestmentHistory).where(InvestmentHistory.user_id == user_id)
        
        if transaction_type:
            query = query.where(InvestmentHistory.transaction_type == transaction_type)
        
        query = query.order_by(desc(InvestmentHistory.created_at)).limit(limit)
        
        history = session.execute(query).scalars().all()
        return history
        
    except Exception as e:
        logger.error(f"❌ Failed to get investment history for user {user_id}: {e}")
        return []


def calculate_earnings_projection(
    current_balance: float,
    weekly_roi_percent: float = 8.0,
    max_cycles: int = 4,
    current_cycles: int = 0
) -> dict:
    """Calculate projected earnings over time"""
    try:
        remaining_cycles = max_cycles - current_cycles
        if remaining_cycles <= 0:
            return {
                "total_projected": current_balance,
                "roi_earnings": 0.0,
                "remaining_cycles": 0,
                "weekly_breakdown": [],
                "completion_date": None
            }
        
        weekly_roi_decimal = weekly_roi_percent / 100.0
        total_projected = current_balance
        roi_earnings = 0.0
        weekly_breakdown = []
        
        for week in range(1, remaining_cycles + 1):
            weekly_roi = current_balance * weekly_roi_decimal
            roi_earnings += weekly_roi
            total_projected += weekly_roi
            
            weekly_breakdown.append({
                "week": week,
                "roi_amount": weekly_roi,
                "cumulative_roi": roi_earnings,
                "projected_balance": total_projected
            })
        
        # Calculate completion date (7 days per cycle)
        completion_date = datetime.utcnow() + timedelta(days=remaining_cycles * 7)
        
        return {
            "total_projected": total_projected,
            "roi_earnings": roi_earnings,
            "remaining_cycles": remaining_cycles,
            "weekly_breakdown": weekly_breakdown,
            "completion_date": completion_date,
            "roi_percentage": weekly_roi_percent
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to calculate earnings projection: {e}")
        return {}


def get_user_financial_summary(session: Session, user_id: int) -> dict:
    """Get comprehensive financial summary for a user"""
    try:
        user = session.execute(
            select(User).where(User.user_id == user_id)
        ).scalar_one_or_none()
        
        if not user:
            return {}
        
        # Get recent transactions
        recent_transactions = get_investment_history(session, user_id, limit=10)
        
        # Calculate earnings projection
        earnings_projection = calculate_earnings_projection(
            current_balance=user.current_balance,
            current_cycles=user.roi_cycles_completed
        )
        
        # Calculate total ROI received
        total_roi_received = sum(
            t.amount for t in recent_transactions 
            if t.transaction_type == "roi_payment"
        )
        
        # Calculate total reinvestments
        total_reinvestments = sum(
            t.amount for t in recent_transactions 
            if t.transaction_type == "reinvestment"
        )
        
        return {
            "user_info": {
                "name": user.name,
                "initial_balance": user.initial_balance,
                "current_balance": user.current_balance,
                "roi_cycles_completed": user.roi_cycles_completed,
                "max_roi_cycles": user.max_roi_cycles,
                "can_withdraw": user.can_withdraw
            },
            "earnings_projection": earnings_projection,
            "transaction_summary": {
                "total_roi_received": total_roi_received,
                "total_reinvestments": total_reinvestments,
                "recent_transactions": len(recent_transactions)
            },
            "next_roi_date": user.next_roi_date
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get financial summary for user {user_id}: {e}")
        return {}
