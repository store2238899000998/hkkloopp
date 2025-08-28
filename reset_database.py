#!/usr/bin/env python3
"""
🔄 Reset Database Script
Clean slate with correct BIGINT schema and David's account
"""

from sqlalchemy import text
from app.db import engine, init_db, get_session
from datetime import datetime, timedelta
from app.models import User, AccessCode, InvestmentHistory


def reset_database():
    """Reset database with correct schema and David's account"""
    print("🔄 Resetting database with correct schema...")
    
    try:
        with engine.connect() as conn:
            # Drop all existing tables
            print("🗑️  Dropping existing tables...")
            conn.execute(text("DROP TABLE IF EXISTS investment_history CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS support_tickets CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS access_codes CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            conn.commit()
            print("✅ Tables dropped")
            
            # Recreate tables with correct schema
            print("🏗️  Recreating tables with BIGINT schema...")
            init_db()
            print("✅ Tables recreated with correct schema")
            
            # Add David back
            print("👤 Adding David back to the system...")
            
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
            with get_session() as session:
                session.add(david_user)
                session.add(access_code)
                session.add(initial_transaction)
                session.commit()
            
            print("✅ David's account created successfully!")
            
            # Verify the schema
            print("\n🔍 Verifying database schema...")
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id';
            """))
            id_column = result.fetchone()
            
            if id_column and id_column[1] == 'bigint':
                print("✅ Users table 'id' column is BIGINT")
            else:
                print("❌ Users table 'id' column is not BIGINT")
            
            print("\n🎉 Database reset completed successfully!")
            print("📋 Access Code: b4d3ef4d")
            print("💰 Initial Balance: $50,000.00")
            print("📧 Email: davidarv@gmail.com")
            print("📱 Phone: +69-809-7789-712")
            print("🌍 Country: Greece")
            
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        raise


if __name__ == "__main__":
    reset_database()
