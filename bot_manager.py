#!/usr/bin/env python3
"""
🤖 Bot Manager - Prevents Telegram Bot Conflicts
Manages bot processes to avoid "terminated by other getUpdates request" errors
"""

import os
import sys
import signal
import subprocess
import time
import psutil
from typing import List, Optional


def find_python_processes() -> List[psutil.Process]:
    """Find all Python processes"""
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                python_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return python_processes


def find_bot_processes() -> List[psutil.Process]:
    """Find processes that might be running our bots"""
    bot_processes = []
    for proc in find_python_processes():
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if any(keyword in cmdline.lower() for keyword in ['main.py', 'start.py', 'bot']):
                bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return bot_processes


def kill_process(proc: psutil.Process) -> bool:
    """Kill a process gracefully, then forcefully if needed"""
    try:
        print(f"🔄 Stopping process {proc.pid} ({proc.info['name']})...")
        proc.terminate()
        
        # Wait for graceful shutdown
        try:
            proc.wait(timeout=5)
            print(f"✅ Process {proc.pid} stopped gracefully")
            return True
        except psutil.TimeoutExpired:
            print(f"⚠️ Process {proc.pid} didn't stop gracefully, forcing...")
            proc.kill()
            proc.wait()
            print(f"✅ Process {proc.pid} force stopped")
            return True
            
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"❌ Error stopping process {proc.pid}: {e}")
        return False


def stop_all_bots() -> int:
    """Stop all running bot processes"""
    print("🛑 Stopping all bot processes...")
    
    bot_processes = find_bot_processes()
    if not bot_processes:
        print("✅ No bot processes found")
        return 0
    
    stopped_count = 0
    for proc in bot_processes:
        if kill_process(proc):
            stopped_count += 1
    
    print(f"🎯 Stopped {stopped_count} bot processes")
    return stopped_count


def check_bot_status() -> None:
    """Check status of bot processes"""
    print("🔍 Checking bot process status...")
    
    bot_processes = find_bot_processes()
    if not bot_processes:
        print("✅ No bot processes running")
        return
    
    print(f"🤖 Found {len(bot_processes)} bot processes:")
    for proc in bot_processes:
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            print(f"  📱 PID {proc.pid}: {cmdline[:80]}...")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"  ❓ PID {proc.pid}: [Access denied]")


def start_bot_safely() -> None:
    """Start bot safely after ensuring no conflicts"""
    print("🚀 Starting bot safely...")
    
    # First, stop any existing bots
    if stop_all_bots() > 0:
        print("⏳ Waiting for processes to fully stop...")
        time.sleep(3)
    
    # Check if any bots are still running
    remaining_bots = find_bot_processes()
    if remaining_bots:
        print("❌ Some bot processes are still running. Please stop them manually:")
        for proc in remaining_bots:
            print(f"  PID {proc.pid}: {proc.info['name']}")
        return
    
    print("✅ All bot processes stopped. Starting fresh...")
    
    # Start the bot using the interactive menu
    try:
        subprocess.run([sys.executable, "start.py"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Bot startup interrupted by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting bot: {e}")


def main():
    """Main bot manager interface"""
    if len(sys.argv) < 2:
        print("""
🤖 Bot Manager - Prevents Telegram Bot Conflicts

Usage:
  python bot_manager.py <command>

Commands:
  status    - Check bot process status
  stop      - Stop all bot processes
  start     - Start bot safely (stops existing first)
  restart   - Stop all bots and start fresh
  help      - Show this help message

Examples:
  python bot_manager.py status
  python bot_manager.py stop
  python bot_manager.py start
  python bot_manager.py restart
""")
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        check_bot_status()
    elif command == "stop":
        stop_all_bots()
    elif command == "start":
        start_bot_safely()
    elif command == "restart":
        stop_all_bots()
        time.sleep(2)
        start_bot_safely()
    elif command == "help":
        print("""
🤖 Bot Manager - Prevents Telegram Bot Conflicts

This tool helps manage Telegram bot processes to avoid the error:
"Conflict: terminated by other getUpdates request; make sure that only one bot instance is running"

Commands:
  status    - Check which bot processes are currently running
  stop      - Gracefully stop all running bot processes
  start     - Start bot safely after ensuring no conflicts
  restart   - Stop all bots and start fresh
  help      - Show this help message

Common Workflow:
  1. Check status: python bot_manager.py status
  2. Stop conflicts: python bot_manager.py stop
  3. Start fresh: python bot_manager.py start

Or use restart: python bot_manager.py restart
""")
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python bot_manager.py help' for usage information")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot manager interrupted by user")
    except Exception as e:
        print(f"❌ Bot manager error: {e}")
        sys.exit(1)
