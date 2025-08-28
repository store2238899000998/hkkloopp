#!/usr/bin/env python3
"""
🔧 Robust Database Setup Script
Handles both local development and production environments
"""

import os
import sys
from datetime import datetime, timedelta

def setup_environment():
    """Set up environment variables for database connection"""
    print("🔧 Setting up environment...")
    
    # Check if we're in production (Render) or local development
    if os.getenv("RENDER") or os.getenv("DATABASE_URL"):
        print("🌐 Production environment detected")
        # Use existing DATABASE_URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in production environment")
            sys.exit(1)
        print(f"✅ Using production database: {database_url[:20]}...")
    else:
        print("🏠 Local development environment detected")
        # Set up local SQLite database
        database_url = "sqlite:///./investment_bot.db"
        os.environ["DATABASE_URL"] = database_url
        print(f"✅ Using local database: {database_url}")
    
    return database_url

def setup_database():
    """Set up database with correct schema"""
    print("\n🏗️  Setting up database...")
    
    try:
        # Import after environment setup
        from app.db import engine, init_db, get_session
        from app.models import User, AccessCode, InvestmentHistory
        
        # Test database connection
        print("🔌 Testing database connection...")
        with engine.connect() as conn:
            print("✅ Database connection successful")
        
        # Initialize database with correct schema
        print("📊 Creating database tables with BIGINT schema...")
        init_db()
        print("✅ Database tables created successfully")
        
        # Verify schema
        print("🔍 Verifying database schema...")
        with engine.connect() as conn:
            # Check if users table has BIGINT id column
            result = conn.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id';
            """)
            id_column = result.fetchone()
            
            if id_column and 'bigint' in id_column[1].lower():
                print("✅ Users table 'id' column is BIGINT")
            else:
                print("❌ Users table 'id' column is not BIGINT")
                raise Exception("Database schema verification failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def add_david_account():
    """Add David's account to the database"""
    print("\n👤 Adding David's account...")
    
    try:
        from app.db import get_session
        from app.models import User, AccessCode, InvestmentHistory
        
        with get_session() as session:
            # Check if David already exists
            existing_user = session.query(User).filter(User.user_id == 123456789).first()
            if existing_user:
                print("✅ David's account already exists")
                return True
            
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
        return True
        
    except Exception as e:
        print(f"❌ Failed to add David's account: {e}")
        return False

def verify_setup():
    """Verify the complete setup"""
    print("\n🔍 Verifying complete setup...")
    
    try:
        from app.db import get_session
        from app.models import User, AccessCode, InvestmentHistory
        
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
                print(f"  • Next ROI: {user.next_roi_date}")
                print(f"  • Can Withdraw: {user.can_withdraw}")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup verification failed: {e}")
        return False

def main():
    """Main setup process"""
    print("Starting robust database setup...")
    print("=" * 50)
    
    try:
        # Step 1: Environment setup
        database_url = setup_environment()
        
        # Step 2: Database setup
        if not setup_database():
            print("❌ Database setup failed. Exiting.")
            sys.exit(1)
        
        # Step 3: Add David's account
        if not add_david_account():
            print("❌ Failed to add David's account. Exiting.")
            sys.exit(1)
        
        # Step 4: Verify everything
        if not verify_setup():
            print("❌ Setup verification failed. Exiting.")
            sys.exit(1)
        
        # Success!
        print("\n" + "=" * 50)
        print("DATABASE SETUP COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("📋 Access Code: b4d3ef4d")
        print("💰 Initial Balance: $50,000.00")
        print("📧 Email: davidarv@gmail.com")
        print("📱 Phone: +69-809-7789-712")
        print("🌍 Country: Greece")
        print("\n💡 Your investment bot is now ready!")
        print("🔧 Next: Deploy to production or run locally")
        
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
