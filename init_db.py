#!/usr/bin/env python3
"""
Initialize the database with clean schema
"""

from app.db import init_db

if __name__ == "__main__":
    print("🗄️ Initializing database...")
    init_db()
    print("✅ Database initialized successfully!")
    print("📋 Tables created:")
    print("   - users")
    print("   - support_tickets")
    print("   - access_codes")
    print("   - investment_history")





