#!/usr/bin/env python3
"""
🔧 Database Migration Script
Adds the investment_history table for tracking financial transactions
"""

from sqlalchemy import text
from app.db import engine, init_db


def migrate_investment_history():
    """Add investment_history table to the database"""
    print("🔧 Starting database migration...")
    
    try:
        # Initialize database (creates all tables)
        init_db()
        print("✅ Database initialized")
        
        # Check if investment_history table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'investment_history'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ investment_history table already exists")
            else:
                print("❌ investment_history table not found - this shouldn't happen with init_db()")
        
        print("🎯 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_investment_history()
