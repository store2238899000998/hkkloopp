#!/usr/bin/env python3
"""
🤖 Bot Conflict Resolution Script
Fixes all Telegram bot conflicts and ensures smooth operation
"""

import os
import sys
import time
import signal
from datetime import datetime

def check_bot_status():
    """Check current bot status and identify conflicts"""
    print("🔍 Checking bot status...")
    
    try:
        # Check if any Python processes are running
        import psutil
        
        python_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(keyword in cmdline.lower() for keyword in ['main.py', 'start.py', 'bot']):
                        python_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if python_processes:
            print(f"⚠️  Found {len(python_processes)} potential bot processes:")
            for proc in python_processes:
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    print(f"  📱 PID {proc.pid}: {cmdline[:80]}...")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    print(f"  ❓ PID {proc.pid}: [Access denied]")
            return python_processes
        else:
            print("✅ No conflicting bot processes found")
            return []
            
    except ImportError:
        print("⚠️  psutil not available - cannot check process status")
        return []
    except Exception as e:
        print(f"❌ Error checking bot status: {e}")
        return []

def stop_conflicting_processes(processes):
    """Stop conflicting bot processes gracefully"""
    if not processes:
        print("✅ No processes to stop")
        return True
    
    print(f"\n🛑 Stopping {len(processes)} conflicting processes...")
    
    stopped_count = 0
    for proc in processes:
        try:
            print(f"🔄 Stopping process {proc.pid}...")
            proc.terminate()
            
            # Wait for graceful shutdown
            try:
                proc.wait(timeout=5)
                print(f"✅ Process {proc.pid} stopped gracefully")
                stopped_count += 1
            except psutil.TimeoutExpired:
                print(f"⚠️  Process {proc.pid} didn't stop gracefully, forcing...")
                proc.kill()
                proc.wait()
                print(f"✅ Process {proc.pid} force stopped")
                stopped_count += 1
                
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"❌ Error stopping process {proc.pid}: {e}")
    
    print(f"🎯 Stopped {stopped_count}/{len(processes)} processes")
    return stopped_count == len(processes)

def verify_environment():
    """Verify environment variables and configuration"""
    print("\n🔧 Verifying environment configuration...")
    
    required_vars = [
        "USER_BOT_TOKEN",
        "ADMIN_BOT_TOKEN", 
        "ADMIN_CHAT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {value[:10]}...")
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Please set these in your .env file or environment")
        return False
    
    print("✅ Environment configuration verified")
    return True

def test_database_connection():
    """Test database connection"""
    print("\n🔌 Testing database connection...")
    
    try:
        from app.db import engine
        
        with engine.connect() as conn:
            print("✅ Database connection successful")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def start_bot_safely():
    """Start the bot safely after conflict resolution"""
    print("\n🚀 Starting bot safely...")
    
    try:
        # Wait a moment for processes to fully stop
        print("⏳ Waiting for processes to fully stop...")
        time.sleep(3)
        
        # Check if any bots are still running
        remaining_bots = check_bot_status()
        if remaining_bots:
            print("❌ Some bot processes are still running. Please stop them manually:")
            for proc in remaining_bots:
                print(f"  PID {proc.pid}: {proc.info['name']}")
            return False
        
        print("✅ All bot processes stopped. Starting fresh...")
        
        # Start the bot using the interactive menu
        import subprocess
        subprocess.run([sys.executable, "start.py"], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot startup interrupted by user")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting bot: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main conflict resolution process"""
    print("🤖 Bot Conflict Resolution Script")
    print("=" * 50)
    
    try:
        # Step 1: Check current status
        conflicting_processes = check_bot_status()
        
        # Step 2: Stop conflicting processes
        if conflicting_processes:
            if not stop_conflicting_processes(conflicting_processes):
                print("❌ Failed to stop all conflicting processes")
                return False
        
        # Step 3: Verify environment
        if not verify_environment():
            print("❌ Environment verification failed")
            return False
        
        # Step 4: Test database connection
        if not test_database_connection():
            print("❌ Database connection test failed")
            return False
        
        # Step 5: Start bot safely
        print("\n🎯 All conflicts resolved! Starting bot...")
        if start_bot_safely():
            print("✅ Bot started successfully!")
            return True
        else:
            print("❌ Failed to start bot")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Conflict resolution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
