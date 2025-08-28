#!/usr/bin/env python3
"""
👤 Add David Back Script
Restores David's account with all original details
"""

from datetime import datetime, timedelta
from app.db import get_session
from app.models import User, AccessCode, InvestmentHistory
from app.services import create_user, credit_user_balance, record_investment_transaction
import uuid


def add_david_back():
    """Add David back to the system with all his details"""
    print("👤 Adding David back to the system...")
    
    try:
        with get_session() as session:
            # 1. Create David's user account
            print("📝 Creating David's user account...")
            
            # Generate a unique ticket ID for the access code
            ticket_id = str(uuid.uuid4())
            
            # Create David's user profile
            david_user = User(
                user_id=123456789,  # You can change this to his actual Telegram ID
                name="David",
                email="davidarv@gmail.com",
                phone="+69-809-7789-712",
                country="Greece",
                initial_balance=50000.00,
                current_balance=50000.00,
                roi_cycles_completed=0,
                max_roi_cycles=4,
                next_roi_date=datetime.utcnow() + timedelta(days=7),  # First ROI in 7 days
                can_withdraw=False,  # Can't withdraw until ROI cycles complete
                created_at=datetime.utcnow() - timedelta(days=30),  # Account created 30 days ago
                updated_at=datetime.utcnow()
            )
            
            session.add(david_user)
            session.commit()
            print("✅ David's user account created")
            
            # 2. Create the access code
            print("🔑 Creating access code...")
            
            access_code = AccessCode(
                code="b4d3ef4d",
                is_used=True,
                used_by=123456789,  # David's Telegram ID
                created_at=datetime.utcnow() - timedelta(days=30),
                used_at=datetime.utcnow() - timedelta(days=30)
            )
            
            session.add(access_code)
            session.commit()
            print("✅ Access code created and marked as used")
            
            # 3. Record the initial deposit transaction
            print("💰 Recording initial deposit transaction...")
            
            initial_transaction = InvestmentHistory(
                user_id=123456789,
                transaction_type="initial_deposit",
                amount=50000.00,
                balance_before=0.00,
                balance_after=50000.00,
                description="Initial investment deposit",
                transaction_metadata='{"deposit_type": "initial_registration", "access_code": "b4d3ef4d"}',
                created_at=datetime.utcnow() - timedelta(days=30)
            )
            
            session.add(initial_transaction)
            session.commit()
            print("✅ Initial deposit transaction recorded")
            
            # 4. Verify everything was created
            print("\n🔍 Verifying David's account...")
            
            # Check user
            user = session.query(User).filter(User.user_id == 123456789).first()
            if user:
                print(f"✅ User found: {user.name} (ID: {user.user_id})")
                print(f"   Balance: ${user.current_balance:.2f}")
                print(f"   ROI Cycles: {user.roi_cycles_completed}/{user.max_roi_cycles}")
                print(f"   Next ROI: {user.next_roi_date}")
                print(f"   Can Withdraw: {user.can_withdraw}")
            else:
                print("❌ User not found!")
            
            # Check access code
            code = session.query(AccessCode).filter(AccessCode.code == "b4d3ef4d").first()
            if code:
                print(f"✅ Access code found: {code.code}")
                print(f"   Used by: {code.used_by}")
                print(f"   Is used: {code.is_used}")
            else:
                print("❌ Access code not found!")
            
            # Check transaction history
            history = session.query(InvestmentHistory).filter(InvestmentHistory.user_id == 123456789).all()
            print(f"✅ Transaction history: {len(history)} records")
            
            print("\n🎉 David has been successfully added back to the system!")
            print("📋 Access Code: b4d3ef4d")
            print("💰 Initial Balance: $50,000.00")
            print("📧 Email: davidarv@gmail.com")
            print("📱 Phone: +69-809-7789-712")
            print("🌍 Country: Greece")
            print("\n💡 David can now use the bot normally with his access code!")
            
    except Exception as e:
        print(f"❌ Error adding David back: {e}")
        session.rollback()
        raise


if __name__ == "__main__":
    add_david_back()
