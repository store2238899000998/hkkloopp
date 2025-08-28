#!/usr/bin/env python3
"""
🔍 Debug Columns Script
Check what columns exist in backup tables
"""

from sqlalchemy import text
from app.db import engine


def debug_columns():
    """Check what columns exist in backup tables"""
    print("🔍 Checking backup table columns...")
    
    try:
        with engine.connect() as conn:
            # Check if backup tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE '%_backup';
            """))
            backup_tables = result.fetchall()
            
            if not backup_tables:
                print("❌ No backup tables found")
                return
            
            print(f"📦 Found {len(backup_tables)} backup tables:")
            for table in backup_tables:
                table_name = table[0]
                print(f"\n🔍 Table: {table_name}")
                
                # Get columns for this table
                result = conn.execute(text(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                
                for col in columns:
                    print(f"  • {col[0]} ({col[1]})")
            
    except Exception as e:
        print(f"❌ Error checking columns: {e}")


if __name__ == "__main__":
    debug_columns()
