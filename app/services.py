#!/usr/bin/env python3
"""
Core business logic services for the investment bot
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Iterable
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import User, SupportTicket, AccessCode, InvestmentHistory
from app.config import settings

logger = logging.getLogger(__name__)


def create_user(session: Session, user_id: int, name: str, initial_balance: float = 0.0, email: str | None = None, phone: str | None = None, country: str | None = None) -> User:
    """Create a new user"""
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
                transaction_metadata={"deposit_type": "initial_registration"}
            )
        except Exception as e:
            logger.error(f"Failed to record initial deposit transaction: {e}")
            # Don't fail user creation for transaction recording issues

    logger.info(f"Created new user: {name} (ID: {user_id}) with balance: {initial_balance}")
    return user


def create_user_with_access_code(session: Session, name: str, initial_balance: float, email: str | None = None, phone: str | None = None, country: str | None = None) -> tuple[AccessCode, str]:
    """Create access code for new user registration. Returns (access_code, message)"""
    access = generate_access_code(session, name=name, initial_balance=initial_balance, expires_in_days=30)
    return access, f"User '{name}' registered successfully!\n\nAccess Code: `{access.code}`\nInitial Balance: {initial_balance:.2f}\nEmail: {email or 'Not provided'}\nPhone: {phone or 'Not provided'}\nCountry: {country or 'Not provided'}\n\nShare this code with the user to activate their account."


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
            transaction_metadata={"credit_type": "admin_manual"}
        )
    except Exception as e:
        logger.error(f"Failed to record admin credit transaction: {e}")
        # Don't fail credit processing for transaction recording issues

    logger.info(f"Credited user {user_id}: {old_balance:.2f} → {user.current_balance:.2f} (+{amount:.2f})")
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
    # Query by code field instead of using session.get (which looks up by primary key)
    access: AccessCode | None = session.query(AccessCode).filter(AccessCode.code == code).first()
    if not access:
        return None
    if access.used_by is not None:
        return None
    # Note: expires_at field doesn't exist in current AccessCode model
    # if access.expires_at and datetime.utcnow() > access.expires_at:
    #     return None
    # Note: preassigned_user_id field doesn't exist in current AccessCode model
    # if access.preassigned_user_id and access.preassigned_user_id != user_id:
    #     return None
    # Use the actual access code data
    user = create_user(session, user_id=user_id, name=access.name, initial_balance=access.initial_balance)
    access.used_by = user_id
    access.used_at = datetime.utcnow()
    return user


# ROI processing

def process_due_roi_for_user(session: Session, user: User) -> bool:
    """Process ROI for a single user if they are due"""
    if not user.next_roi_date:
        logger.warning(f"User {user.user_id} has no next_roi_date set")
        return False

    if datetime.utcnow() < user.next_roi_date:
        return False

    if user.roi_cycles_completed >= settings.max_roi_cycles:
        logger.info(f"User {user.user_id} has completed all ROI cycles ({user.roi_cycles_completed}/{settings.max_roi_cycles})")
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
        logger.info(f"User {user.user_id} completed all ROI cycles - withdrawal enabled")

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
            transaction_metadata={
                "cycle_number": user.roi_cycles_completed,
                "roi_percentage": settings.weekly_roi_percent,
                "base_amount": user.initial_balance
            }
        )
    except Exception as e:
        logger.error(f"Failed to record ROI transaction: {e}")
        # Don't fail ROI processing for transaction recording issues

    logger.info(
        f"ROI processed for user {user.user_id}: "
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
        status="open"
    )
    session.add(ticket)
    session.flush()
    logger.info(f"Created support ticket {ticket.ticket_id} for user {user_id}")
    return ticket


def get_support_tickets(session: Session, status: str | None = None, limit: int | None = None) -> list[SupportTicket]:
    query = session.query(SupportTicket)
    if status:
        query = query.filter(SupportTicket.status == status)
    query = query.order_by(SupportTicket.created_at.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def update_ticket_status(session: Session, ticket_id: str, status: str) -> bool:
    ticket = session.query(SupportTicket).filter(SupportTicket.ticket_id == ticket_id).first()
    if not ticket:
        return False
    ticket.status = status
    session.flush()
    logger.info(f"Updated ticket {ticket_id} status to {status}")
    return True


# Investment history tracking

def record_investment_transaction(
    session: Session,
    user_id: int,
    transaction_type: str,
    amount: float,
    balance_before: float,
    balance_after: float,
    description: str,
    transaction_metadata: dict | None = None
) -> InvestmentHistory:
    """Record a transaction in the investment history"""
    try:
        # Convert metadata to JSON string if provided
        metadata_str = None
        if transaction_metadata:
            import json
            metadata_str = json.dumps(transaction_metadata)

        transaction = InvestmentHistory(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            transaction_metadata=metadata_str
        )
        session.add(transaction)
        session.flush()
        
        logger.info(f"Recorded {transaction_type} transaction: {amount:.2f} for user {user_id}")
        return transaction
        
    except Exception as e:
        logger.error(f"Failed to record transaction: {e}")
        raise


def get_investment_history(session: Session, user_id: int, limit: int = 50) -> list[InvestmentHistory]:
    """Get investment history for a user"""
    return session.query(InvestmentHistory)\
        .filter(InvestmentHistory.user_id == user_id)\
        .order_by(InvestmentHistory.created_at.desc())\
        .limit(limit)\
        .all()


def calculate_earnings_projection(
    current_balance: float,
    current_cycles: int,
    max_cycles: int = 4,
    weekly_roi_percent: float = 8.0
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
        logger.error(f"Failed to calculate earnings projection: {e}")
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
        logger.error(f"Failed to get financial summary for user {user_id}: {e}")
        return {}


# Admin management functions

def debit_user_balance(session: Session, user_id: int, amount: float) -> Optional[User]:
    """Debit (reduce) user balance by specified amount"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return None
    
    if (user.current_balance or 0.0) < amount:
        return None
    
    old_balance = user.current_balance
    user.current_balance -= amount
    
    # Record the admin debit transaction
    try:
        record_investment_transaction(
            session=session,
            user_id=user_id,
            transaction_type="admin_debit",
            amount=amount,
            balance_before=old_balance,
            balance_after=user.current_balance,
            description="Admin Debit",
            transaction_metadata={"debit_type": "admin_manual"}
        )
    except Exception as e:
        logger.error(f"Failed to record admin debit transaction: {e}")
    
    logger.info(f"Debited user {user_id}: {old_balance:.2f} → {user.current_balance:.2f} (-{amount:.2f})")
    return user


def transfer_balance(session: Session, from_user_id: int, to_user_id: int, amount: float) -> tuple[bool, str]:
    """Transfer balance between two users"""
    from_user = session.execute(
        select(User).where(User.user_id == from_user_id)
    ).scalar_one_or_none()
    
    to_user = session.execute(
        select(User).where(User.user_id == to_user_id)
    ).scalar_one_or_none()
    
    if not from_user or not to_user:
        return False, "One or both users not found"
    
    if (from_user.current_balance or 0.0) < amount:
        return False, "Insufficient balance for transfer"
    
    # Perform transfer
    from_user.current_balance -= amount
    to_user.current_balance += amount
    
    # Record transactions
    try:
        record_investment_transaction(
            session=session,
            user_id=from_user_id,
            transaction_type="transfer_out",
            amount=amount,
            balance_before=from_user.current_balance + amount,
            balance_after=from_user.current_balance,
            description=f"Transfer to user {to_user_id}",
            transaction_metadata={"transfer_type": "user_to_user", "recipient_id": to_user_id}
        )
        
        record_investment_transaction(
            session=session,
            user_id=to_user_id,
            transaction_type="transfer_in",
            amount=amount,
            balance_before=to_user.current_balance - amount,
            balance_after=to_user.current_balance,
            description=f"Transfer from user {from_user_id}",
            transaction_metadata={"transfer_type": "user_to_user", "sender_id": from_user_id}
        )
    except Exception as e:
        logger.error(f"Failed to record transfer transactions: {e}")
        return False, f"Transfer failed: {e}"
    
    logger.info(f"Transfer successful: {amount:.2f} from {from_user_id} to {to_user_id}")
    return True, f"Transfer successful: {amount:.2f}"


def force_roi_payment(session: Session, user_id: int) -> tuple[bool, str]:
    """Force immediate ROI payment for a user if eligible"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    if user.roi_cycles_completed >= settings.max_roi_cycles:
        return False, "User has completed all ROI cycles"
    
    if not user.next_roi_date:
        return False, "User has no ROI schedule set"
    
    # Force ROI processing
    success = process_due_roi_for_user(session, user)
    if success:
        return True, f"ROI payment processed: {user.roi_cycles_completed}/{settings.max_roi_cycles} cycles"
    else:
        return False, "ROI payment not eligible at this time"


def adjust_roi_cycles(session: Session, user_id: int, cycles: int) -> tuple[bool, str]:
    """Adjust user's ROI cycles completed"""
    if cycles < 0 or cycles > settings.max_roi_cycles:
        return False, f"Invalid cycle count. Must be 0-{settings.max_roi_cycles}"
    
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    old_cycles = user.roi_cycles_completed
    user.roi_cycles_completed = cycles
    
    # Update withdrawal permission
    user.can_withdraw = (cycles >= settings.max_roi_cycles)
    
    # Adjust next ROI date if needed
    if cycles == 0:
        user.next_roi_date = datetime.utcnow() + timedelta(days=7)
    elif cycles < settings.max_roi_cycles:
        # Set next ROI date based on remaining cycles
        remaining_cycles = settings.max_roi_cycles - cycles
        user.next_roi_date = datetime.utcnow() + timedelta(days=7)
    
    logger.info(f"Adjusted ROI cycles for user {user_id}: {old_cycles} → {cycles}")
    return True, f"ROI cycles adjusted: {cycles}/{settings.max_roi_cycles}"


def enable_user_withdrawal(session: Session, user_id: int) -> tuple[bool, str]:
    """Enable withdrawal for a user"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    user.can_withdraw = True
    logger.info(f"Withdrawal enabled for user {user_id}")
    return True, "Withdrawal enabled successfully"


def disable_user_withdrawal(session: Session, user_id: int) -> tuple[bool, str]:
    """Disable withdrawal for a user"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    user.can_withdraw = False
    logger.info(f"Withdrawal disabled for user {user_id}")
    return True, "Withdrawal disabled successfully"


def set_next_roi_date(session: Session, user_id: int, days_from_now: int) -> tuple[bool, str]:
    """Set next ROI date for a user"""
    if days_from_now < 0:
        return False, "Days must be positive"
    
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    new_date = datetime.utcnow() + timedelta(days=days_from_now)
    old_date = user.next_roi_date
    user.next_roi_date = new_date
    
    logger.info(f"Set next ROI date for user {user_id}: {old_date} → {new_date}")
    return True, f"Next ROI date set to {new_date.strftime('%Y-%m-%d')}"


def reset_user_roi_cycles(session: Session, user_id: int) -> tuple[bool, str]:
    """Reset user's ROI cycles to 0"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    old_cycles = user.roi_cycles_completed
    user.roi_cycles_completed = 0
    user.can_withdraw = False
    user.next_roi_date = datetime.utcnow() + timedelta(days=7)
    
    logger.info(f"Reset ROI cycles for user {user_id}: {old_cycles} → 0")
    return True, "ROI cycles reset to 0"


def increment_roi_cycles(session: Session, user_id: int) -> tuple[bool, str]:
    """Increment user's ROI cycles by 1 and add ROI payment to balance"""
    user = session.execute(
        select(User).where(User.user_id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        return False, "User not found"
    
    if user.roi_cycles_completed >= settings.max_roi_cycles:
        return False, f"User already completed all {settings.max_roi_cycles} ROI cycles"
    
    # Calculate ROI amount (8% of initial balance)
    roi_amount = (user.initial_balance or 0.0) * (settings.weekly_roi_percent / 100.0)
    old_balance = user.current_balance
    old_cycles = user.roi_cycles_completed
    
    # Increment cycles and add ROI payment to balance
    user.roi_cycles_completed += 1
    user.current_balance = (user.current_balance or 0.0) + roi_amount
    
    # Update withdrawal permission
    user.can_withdraw = (user.roi_cycles_completed >= settings.max_roi_cycles)
    
    # Set next ROI date if not at max cycles
    if user.roi_cycles_completed < settings.max_roi_cycles:
        user.next_roi_date = datetime.utcnow() + timedelta(days=7)
    
    # Record the ROI payment transaction (as if it was a real ROI payment)
    try:
        record_investment_transaction(
            session=session,
            user_id=user_id,
            transaction_type="roi_payment",
            amount=roi_amount,
            balance_before=old_balance,
            balance_after=user.current_balance,
            description=f"ROI Payment - Cycle {user.roi_cycles_completed} (Admin)",
            transaction_metadata={
                "cycle_number": user.roi_cycles_completed,
                "roi_percentage": settings.weekly_roi_percent,
                "base_amount": user.initial_balance,
                "admin_action": True,
                "previous_cycles": old_cycles
            }
        )
    except Exception as e:
        logger.error(f"Failed to record admin ROI payment transaction: {e}")
    
    logger.info(
        f"Admin incremented ROI cycles for user {user_id}: "
        f"cycle {old_cycles}→{user.roi_cycles_completed}, "
        f"balance {old_balance:.2f}→{user.current_balance:.2f} "
        f"(+{roi_amount:.2f} ROI payment)"
    )
    
    if user.can_withdraw:
        return True, f"ROI cycle incremented to {user.roi_cycles_completed}/{settings.max_roi_cycles} - +{roi_amount:.2f} added to balance - Withdrawal unlocked! 🎉"
    else:
        return True, f"ROI cycle incremented to {user.roi_cycles_completed}/{settings.max_roi_cycles} - +{roi_amount:.2f} added to balance"
