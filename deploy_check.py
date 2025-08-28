ng t#!/usr/bin/env python3
"""
🚀 Deployment Check Script
Prevents multiple bot instances from running simultaneously on Render
"""

import os
import time
import signal
import sys
from datetime import datetime


def check_deployment_lock():
    """Check if deployment is already in progress"""
    lock_file = "/tmp/bot_deployment.lock"
    
    if os.path.exists(lock_file):
        # Check if lock is stale (older than 5 minutes)
        lock_time = os.path.getmtime(lock_file)
        if time.time() - lock_time > 300:  # 5 minutes
            print("⚠️  Removing stale deployment lock")
            os.remove(lock_file)
        else:
            print("❌ Deployment already in progress (lock file exists)")
            print(f"   Lock created: {datetime.fromtimestamp(lock_time)}")
            return False
    
    # Create lock file
    with open(lock_file, 'w') as f:
        f.write(f"Deployment started at {datetime.now()}")
    
    print("✅ Deployment lock created")
    return True


def cleanup_deployment_lock():
    """Remove deployment lock file"""
    lock_file = "/tmp/bot_deployment.lock"
    if os.path.exists(lock_file):
        os.remove(lock_file)
        print("✅ Deployment lock removed")


def main():
    """Main deployment check"""
    print("🚀 Starting deployment check...")
    print(f"🆔 Process ID: {os.getpid()}")
    print(f"⏰ Start time: {datetime.now()}")
    
    # Set up signal handlers for cleanup
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, cleaning up...")
        cleanup_deployment_lock()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Check deployment lock
        if not check_deployment_lock():
            print("❌ Cannot proceed with deployment")
            sys.exit(1)
        
        print("✅ Deployment check passed")
        print("🚀 Starting main application...")
        
        # Import and run main app
        from main import app
        import uvicorn
        
        # Start the FastAPI app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", "10000")),
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        cleanup_deployment_lock()
        sys.exit(1)
    finally:
        cleanup_deployment_lock()


if __name__ == "__main__":
    main()
