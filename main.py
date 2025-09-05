from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager
import logging

from app.db import init_db
from scheduler.jobs import start_scheduler, stop_scheduler, catchup_missed_roi
from bots.user_bot import run_user_bot, stop_user_bot
from bots.admin_bot import run_admin_bot, stop_admin_bot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle with recovery"""
    logger.info("🚀 Starting Investment Bot system...")

    # 1. Init database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise

    # 2. Start scheduler
    try:
        start_scheduler()
        logger.info("✅ Scheduler started")
    except Exception as e:
        logger.error(f"❌ Scheduler failed: {e}")
        raise

    # 3. Run immediate ROI catch-up to recover from any downtime
    try:
        logger.info("🔄 Running ROI catch-up process...")
        processed_users, total_payments = await catchup_missed_roi()
        if total_payments > 0:
            logger.info(f"🎯 Recovered {total_payments} missed ROI payments for {processed_users} users")
        else:
            logger.info("✅ No missed ROI payments found")
    except Exception as e:
        logger.error(f"❌ ROI catch-up failed: {e}")
        # Don't fail startup for catch-up issues

    # 4. Start bots concurrently in background with startup delay
    try:
        # Add small delay to prevent multiple instances from starting simultaneously
        await asyncio.sleep(2)
        
        # Start bots with staggered startup
        user_bot_task = asyncio.create_task(run_user_bot())
        await asyncio.sleep(1)  # Stagger bot startup
        admin_bot_task = asyncio.create_task(run_admin_bot())
        
        logger.info("🤖 Bots started (user + admin)")
        
        # Wait for both bots to start
        await asyncio.sleep(3)
        
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        raise

    yield  # 👉 FastAPI runs here

    # 5. Shutdown hooks with graceful cleanup
    logger.info("🛑 Shutting down Investment Bot system...")
    try:
        stop_scheduler()
        logger.info("✅ Scheduler stopped gracefully")
    except Exception as e:
        logger.error(f"❌ Scheduler shutdown error: {e}")
    
    try:
        await stop_user_bot()
        logger.info("✅ User bot stopped gracefully")
    except Exception as e:
        logger.error(f"❌ User bot shutdown error: {e}")
    
    try:
        await stop_admin_bot()
        logger.info("✅ Admin bot stopped gracefully")
    except Exception as e:
        logger.error(f"❌ Admin bot shutdown error: {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello from Investment Bot API + Bots 🚀"}


@app.get("/health")
async def health():
    """Enhanced health check endpoint"""
    from datetime import datetime
    import os
    return {
        "status": "healthy",
        "service": "Investment Bot",
        "timestamp": datetime.now().isoformat(),
        "process_id": os.getpid(),
        "deployment_time": os.getenv("DEPLOYMENT_TIME", "unknown")
    }


@app.post("/admin/recovery/catchup-roi")
async def manual_catchup_roi():
    """Manual endpoint to trigger ROI catch-up (admin only)"""
    try:
        processed_users, total_payments = await catchup_missed_roi()
        return {
            "success": True,
            "message": f"ROI catch-up completed: {processed_users} users, {total_payments} payments",
            "processed_users": processed_users,
            "total_payments": total_payments
        }
    except Exception as e:
        logger.error(f"Manual ROI catch-up failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }



