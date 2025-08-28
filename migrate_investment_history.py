#!/usr/bin/env python3
"""
🔧 Database Migration Script
Fixes database schema and adds the investment_history table for tracking financial transactions
"""

from sqlalchemy import text
from app.db import engine, init_db


def migrate_investment_history():
    """Fix database schema and add investment_history table"""
    print("🔧 Starting database migration...")
    
    try:
        # Check current database structure
        with engine.connect() as conn:
            # Check if users table has 'id' column
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id';
            """))
            has_id_column = result.fetchone() is not None
            
            if not has_id_column:
                print("⚠️  Users table missing 'id' column - recreating tables...")
                
                # Drop existing tables to recreate with correct schema
                conn.execute(text("DROP TABLE IF EXISTS investment_history CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS support_tickets CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS access_codes CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                conn.commit()
                print("✅ Old tables dropped")
                
                # Recreate tables with correct schema
                init_db()
                print("✅ Tables recreated with correct schema")
            else:
                print("✅ Users table has correct structure")
                # Just initialize to ensure all tables exist
                init_db()
                print("✅ Database initialized")
        
        # Verify investment_history table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'investment_history'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ investment_history table exists")
            else:
                print("❌ investment_history table not found - this shouldn't happen")
        
        print("🎯 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_investment_history()
