#!/usr/bin/env python3
"""
Simple database test script
"""

from app.db import get_session
from app.models import User, AccessCode, InvestmentHistory

def test_database():
    """Test database functionality"""
    print("Testing database...")
    
    try:
        with get_session() as session:
            # Check users
            users = session.query(User).all()
            print(f"Total users: {len(users)}")
            
            # Check access codes
            codes = session.query(AccessCode).all()
            print(f"Total access codes: {len(codes)}")
            
            # Check investment history
            history = session.query(InvestmentHistory).all()
            print(f"Total transactions: {len(history)}")
            
            if users:
                user = users[0]
                print(f"\nFirst user:")
                print(f"  Name: {user.name}")
                print(f"  ID: {user.id}")
                print(f"  User ID: {user.user_id}")
                print(f"  Balance: ${user.current_balance:.2f}")
            
            print("\nDatabase test completed successfully!")
            
    except Exception as e:
        print(f"Database test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database()
