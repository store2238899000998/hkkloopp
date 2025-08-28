#!/usr/bin/env python3
"""
Manual script to add David's account step by step
"""

from app.db import get_session
from app.models import User, AccessCode, InvestmentHistory
from datetime import datetime, timedelta

def add_david_manual():
    """Add David's account manually"""
    print("Adding David's account manually...")
    
    try:
        with get_session() as session:
            # Step 1: Create David's user account
            print("Step 1: Creating user account...")
            david_user = User(
                user_id=123456789,
                name="David",
                email="davidarv@gmail.com",
                phone="+69-809-7789-712",
                country="Greece",
                initial_balance=50000.00,
                current_balance=50000.00,
                roi_cycles_completed=0,
                max_roi_cycles=4,
                next_roi_date=datetime.utcnow() + timedelta(days=7),
                can_withdraw=False,
                created_at=datetime.utcnow() - timedelta(days=30),
                updated_at=datetime.utcnow()
            )
            
            session.add(david_user)
            session.commit()
            print("User account created successfully!")
            
            # Step 2: Create access code
            print("Step 2: Creating access code...")
            access_code = AccessCode(
                code="b4d3ef4d",
                is_used=True,
                used_by=123456789,
                created_at=datetime.utcnow() - timedelta(days=30),
                used_at=datetime.utcnow() - timedelta(days=30)
            )
            
            session.add(access_code)
            session.commit()
            print("Access code created successfully!")
            
            # Step 3: Create transaction history
            print("Step 3: Creating transaction history...")
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
            print("Transaction history created successfully!")
            
            print("\nDavid's account created successfully!")
            return True
            
    except Exception as e:
        print(f"Failed to add David's account: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    add_david_manual()
