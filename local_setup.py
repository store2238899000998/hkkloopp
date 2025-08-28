#!/usr/bin/env python3
"""
🏠 Local Development Setup Script
Sets up SQLite database with correct BIGINT schema and David's account
"""

import os
import sys
from datetime import datetime, timedelta

# Set environment variable for SQLite database
os.environ["DATABASE_URL"] = "sqlite:///./investment_bot.db"

# Now import after setting environment
from app.db import engine, init_db, get_session
from app.models import User, AccessCode, InvestmentHistory


def setup_local_database():
    """Set up local SQLite database with correct schema"""
    print("🏠 Setting up local SQLite database...")
    
    try:
        # Initialize database with correct schema
        print("🏗️  Creating database tables with BIGINT schema...")
        init_db()
        print("✅ Database tables created")
        
        # Add David's account
        print("👤 Adding David's account...")
        
        with get_session() as session:
            # Create David's user account
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
                next_roi_date=datetime.utcnow() + timedelta(days=7),
                can_withdraw=False,
                created_at=datetime.utcnow() - timedelta(days=30),
                updated_at=datetime.utcnow()
            )
            
            # Create the access code
            access_code = AccessCode(
                code="b4d3ef4d",
                is_used=True,
                used_by=123456789,
                created_at=datetime.utcnow() - timedelta(days=30),
                used_at=datetime.utcnow() - timedelta(days=30)
            )
            
            # Record the initial deposit transaction
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
            
            # Add everything to session
            session.add(david_user)
            session.add(access_code)
            session.add(initial_transaction)
            # Session will auto-commit due to context manager
        
        print("✅ David's account created successfully!")
        
        # Verify the setup
        print("\n🔍 Verifying database setup...")
        with get_session() as session:
            users = session.query(User).all()
            print(f"👥 Total users: {len(users)}")
            
            codes = session.query(AccessCode).all()
            print(f"🔑 Total access codes: {len(codes)}")
            
            history = session.query(InvestmentHistory).all()
            print(f"📊 Total transactions: {len(history)}")
            
            if users:
                user = users[0]
                print(f"\n📋 User details:")
                print(f"  • Name: {user.name}")
                print(f"  • Telegram ID: {user.user_id}")
                print(f"  • Balance: ${user.current_balance:.2f}")
                print(f"  • ROI Cycles: {user.roi_cycles_completed}/{user.max_roi_cycles}")
        
        print("\n🎉 Local database setup completed successfully!")
        print("📋 Access Code: b4d3ef4d")
        print("💰 Initial Balance: $50,000.00")
        print("📧 Email: davidarv@gmail.com")
        print("📱 Phone: +69-809-7789-712")
        print("🌍 Country: Greece")
        print("\n💡 You can now run the bot locally!")
        
    except Exception as e:
        print(f"❌ Local setup failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    setup_local_database()
