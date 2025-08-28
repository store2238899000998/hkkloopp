#!/usr/bin/env python3
"""
🔒 Safe Database Migration Script
Preserves existing user data while fixing schema issues
"""

from sqlalchemy import text
from app.db import engine, init_db


def safe_migrate():
    """Safely migrate database without losing data"""
    print("🔒 Starting SAFE database migration...")
    
    try:
        with engine.connect() as conn:
            # Check if users table has 'id' column with correct data type
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'id';
            """))
            id_column_info = result.fetchone()
            has_id_column = id_column_info is not None
            has_bigint_id = has_id_column and id_column_info[1] == 'bigint'
            
            if not has_id_column or not has_bigint_id:
                if not has_id_column:
                    print("⚠️  Users table missing 'id' column - performing safe migration...")
                else:
                    print("⚠️  Users table 'id' column is not BIGINT - performing safe migration...")
                
                # Check if we have existing data
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                
                if user_count > 0:
                    print(f"⚠️  Found {user_count} existing users - BACKING UP DATA FIRST!")
                    
                    # Create backup tables
                    print("📦 Creating backup tables...")
                    conn.execute(text("CREATE TABLE users_backup AS SELECT * FROM users"))
                    conn.execute(text("CREATE TABLE support_tickets_backup AS SELECT * FROM support_tickets"))
                    conn.execute(text("CREATE TABLE access_codes_backup AS SELECT * FROM access_codes"))
                    conn.execute(text("CREATE TABLE investment_history_backup AS SELECT * FROM investment_history"))
                    conn.commit()
                    print("✅ Backup tables created")
                    
                    # Now drop and recreate with correct schema
                    print("🔄 Recreating tables with correct schema...")
                    conn.execute(text("DROP TABLE IF EXISTS investment_history CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS support_tickets CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS access_codes CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                    conn.commit()
                    print("✅ Old tables dropped")
                    
                    # Recreate tables with correct schema
                    init_db()
                    print("✅ Tables recreated with correct schema")
                    
                    # Restore data with new schema
                    print("🔄 Restoring user data...")
                    conn.execute(text("""
                        INSERT INTO users (user_id, name, email, phone, country, initial_balance, 
                                        current_balance, roi_cycles_completed, max_roi_cycles, 
                                        next_roi_date, can_withdraw, created_at, updated_at)
                        SELECT user_id, name, email, phone, country, initial_balance, 
                               current_balance, roi_cycles_completed, max_roi_cycles, 
                               next_roi_date, can_withdraw, created_at, updated_at
                        FROM users_backup
                    """))
                    
                    # Restore other data
                    conn.execute(text("""
                        INSERT INTO support_tickets (ticket_id, user_id, message, status, created_at, updated_at)
                        SELECT ticket_id, user_id, message, status, created_at, updated_at
                        FROM support_tickets_backup
                    """))
                    
                    conn.execute(text("""
                        INSERT INTO access_codes (code, is_used, used_by, created_at, used_at)
                        SELECT code, is_used, used_by, created_at, used_at
                        FROM access_codes_backup
                    """))
                    
                    conn.execute(text("""
                        INSERT INTO investment_history (user_id, transaction_type, amount, 
                                                     balance_before, balance_after, description, 
                                                     transaction_metadata, created_at)
                        SELECT user_id, transaction_type, amount, balance_before, balance_after, 
                               description, transaction_metadata, created_at
                        FROM investment_history_backup
                    """))
                    
                    conn.commit()
                    print("✅ User data restored successfully!")
                    
                    # Clean up backup tables
                    print("🧹 Cleaning up backup tables...")
                    conn.execute(text("DROP TABLE users_backup"))
                    conn.execute(text("DROP TABLE support_tickets_backup"))
                    conn.execute(text("DROP TABLE access_codes_backup"))
                    conn.execute(text("DROP TABLE investment_history_backup"))
                    conn.commit()
                    print("✅ Backup tables cleaned up")
                    
                else:
                    print("✅ No existing users found - safe to recreate tables")
                    # Safe to drop and recreate
                    conn.execute(text("DROP TABLE IF EXISTS investment_history CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS support_tickets CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS access_codes CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
                    conn.commit()
                    
                    init_db()
                    print("✅ Tables recreated with correct schema")
            else:
                print("✅ Users table has correct structure")
                init_db()
                print("✅ Database initialized")
        
        # Verify tables exist
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
                print("❌ investment_history table not found")
        
        print("🎯 Safe migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Safe migration failed: {e}")
        raise


if __name__ == "__main__":
    safe_migrate()
