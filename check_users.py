#!/usr/bin/env python3
"""
🔍 Check User Data Script
Verifies that user data exists after migration
"""

from app.db import get_session
from app.models import User, SupportTicket, AccessCode, InvestmentHistory


def check_user_data():
    """Check if user data exists in the database"""
    print("🔍 Checking user data after migration...")
    
    try:
        with get_session() as session:
            # Check users
            users = session.query(User).all()
            print(f"👥 Total users: {len(users)}")
            
            if users:
                print("\n📋 User details:")
                for user in users[:5]:  # Show first 5 users
                    print(f"  • {user.name} (Telegram ID: {user.user_id})")
                    print(f"    Balance: ${user.current_balance:.2f}")
                    print(f"    ROI Cycles: {user.roi_cycles_completed}/{user.max_roi_cycles}")
                    print(f"    Created: {user.created_at}")
                    print()
            else:
                print("❌ No users found in database")
            
            # Check support tickets
            tickets = session.query(SupportTicket).all()
            print(f"🎫 Total support tickets: {len(tickets)}")
            
            # Check access codes
            codes = session.query(AccessCode).all()
            print(f"🔑 Total access codes: {len(codes)}")
            
            # Check investment history
            history = session.query(InvestmentHistory).all()
            print(f"📊 Total investment history records: {len(history)}")
            
            print("\n✅ Database check completed!")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")


if __name__ == "__main__":
    check_user_data()
