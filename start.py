#!/usr/bin/env python3
"""
🚀 Investment Bot Startup Script
Simple interactive launcher for all services
"""

import os
import sys
import subprocess
import time


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def show_menu():
    """Display the startup menu"""
    clear_screen()
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🚀 INVESTMENT BOT                        ║
║                        Startup Menu                          ║
╚══════════════════════════════════════════════════════════════╝

🎯 Choose what to start:

1️⃣  🚀 START EVERYTHING (API + Bots + Scheduler) - RECOMMENDED
2️⃣  🤖 Bots + Scheduler Only (for development)
3️⃣  🌐 API Only (FastAPI server)
4️⃣  📱 User Bot Only
5️⃣  🔐 Admin Bot Only
6️⃣  📊 Database Setup Only
7️⃣  ❌ Exit

Enter your choice (1-7): """)


def start_everything():
    """Start all services"""
    print("\n🚀 Starting complete Investment Bot system...")
    print("⏳ This will start API, both bots, and scheduler...")
    
    try:
        # Start everything using main.py
        subprocess.run([sys.executable, "main.py", "all"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting services: {e}")


def start_bots_only():
    """Start bots and scheduler only"""
    print("\n🤖 Starting bots and scheduler...")
    try:
        subprocess.run([sys.executable, "main.py", "bots"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting bots: {e}")


def start_api_only():
    """Start API only"""
    print("\n🌐 Starting FastAPI server...")
    try:
        subprocess.run([sys.executable, "main.py", "api"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 API startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting API: {e}")


def start_user_bot():
    """Start user bot only"""
    print("\n📱 Starting user bot...")
    try:
        subprocess.run([sys.executable, "-c", "import asyncio; from bots.user_bot import run_user_bot; asyncio.run(run_user_bot())"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 User bot startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting user bot: {e}")


def start_admin_bot():
    """Start admin bot only"""
    print("\n🔐 Starting admin bot...")
    try:
        subprocess.run([sys.executable, "-c", "import asyncio; from bots.admin_bot import run_admin_bot; asyncio.run(run_admin_bot())"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Admin bot startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting admin bot: {e}")


def setup_database():
    """Setup database only"""
    print("\n📊 Setting up database...")
    try:
        from app.db import init_db
        init_db()
        print("✅ Database initialized successfully!")
        input("\nPress Enter to continue...")
    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        input("\nPress Enter to continue...")


def main():
    """Main startup loop"""
    while True:
        show_menu()
        choice = input().strip()
        
        if choice == "1":
            start_everything()
        elif choice == "2":
            start_bots_only()
        elif choice == "3":
            start_api_only()
        elif choice == "4":
            start_user_bot()
        elif choice == "5":
            start_admin_bot()
        elif choice == "6":
            setup_database()
        elif choice == "7":
            print("\n👋 Goodbye! Exiting...")
            break
        else:
            print("\n❌ Invalid choice. Please enter 1-7.")
            time.sleep(1)


if __name__ == "__main__":
    main()
