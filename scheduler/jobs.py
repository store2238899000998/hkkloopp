from __future__ import annotations

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy import select

from app.db import get_session, engine
from app.models import User
from app.services import process_weekly_roi, list_users, process_due_roi_for_user
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use database for job persistence
jobstores = {
    'default': SQLAlchemyJobStore(url=settings.database_url, engine=engine)
}

scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=settings.timezone)


async def catchup_missed_roi():
    """Process any ROI that was missed during server downtime"""
    logger.info("🔄 Starting ROI catch-up process...")
    processed_count = 0
    total_catchup = 0
    
    with get_session() as session:
        users = session.execute(select(User)).scalars().all()
        
        for user in users:
            user_catchup = 0
            # Process all missed ROI payments
            while (user.next_roi_date and 
                   datetime.utcnow() >= user.next_roi_date and 
                   user.roi_cycles_completed < settings.max_roi_cycles):
                
                if process_due_roi_for_user(session, user):
                    user_catchup += 1
                    total_catchup += 1
                    logger.info(f"✅ Caught up ROI for user {user.user_id}: cycle {user.roi_cycles_completed}")
                else:
                    break  # Stop if processing fails
            
            if user_catchup > 0:
                processed_count += 1
                logger.info(f"🔄 User {user.user_id}: caught up {user_catchup} missed ROI payments")
    
    logger.info(f"🎯 ROI catch-up complete: {processed_count} users processed, {total_catchup} total payments")
    return processed_count, total_catchup


async def job_weekly_roi():
    """Process weekly ROI for all due users"""
    try:
        logger.info("🔄 Starting weekly ROI processing...")
        with get_session() as session:
            processed = process_weekly_roi(session)
            logger.info(f"✅ Weekly ROI processed: {processed} users received payments")
        return processed
    except Exception as e:
        logger.error(f"❌ Weekly ROI job failed: {e}")
        return 0


async def job_daily_ping():
    """Send daily countdown messages to all users"""
    try:
        logger.info("📱 Starting daily user notifications...")
        bot = Bot(token=settings.user_bot_token)
        with get_session() as session:
            users = list_users(session)
            sent_count = 0
            
            for user in users:
                try:
                    remaining_days = 0
                    if user.next_roi_date:
                        remaining_days = max(0, (user.next_roi_date.date() - datetime.utcnow().date()).days)
                    
                    text = (
                        f"🌞 Good Morning!\n\n"
                        f"💼 Balance: {user.current_balance:.2f}\n"
                        f"📈 ROI Cycle: {user.roi_cycles_completed} / {settings.max_roi_cycles}\n"
                        f"⏳ Next ROI in: {remaining_days} days"
                    )
                    
                    await bot.send_message(chat_id=user.user_id, text=text)
                    sent_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to send notification to user {user.user_id}: {e}")
                    # Don't fail the entire job for one user
            
            logger.info(f"✅ Daily notifications sent: {sent_count}/{len(users)} users")
            
    except Exception as e:
        logger.error(f"❌ Daily ping job failed: {e}")


async def job_health_check():
    """Health check job to ensure system is running"""
    try:
        logger.info("💓 System health check: OK")
        return True
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


def setup_jobs():
    """Setup all scheduled jobs with error handling"""
    try:
        # Run weekly ROI check every day at 00:10 to catch due users
        scheduler.add_job(
            job_weekly_roi, 
            "cron", 
            hour=0, 
            minute=10, 
            id="weekly_roi",
            name="Weekly ROI Processing",
            replace_existing=True
        )
        
        # Daily user countdown message at 08:00
        scheduler.add_job(
            job_daily_ping, 
            "cron", 
            hour=8, 
            minute=0, 
            id="daily_ping",
            name="Daily User Notifications",
            replace_existing=True
        )
        
        # Health check every hour
        scheduler.add_job(
            job_health_check,
            "interval",
            hours=1,
            id="health_check",
            name="System Health Check",
            replace_existing=True
        )
        
        logger.info("✅ All scheduled jobs configured successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup jobs: {e}")
        raise


def start_scheduler():
    """Start the scheduler with recovery"""
    try:
        setup_jobs()
        scheduler.start()
        logger.info("🚀 Scheduler started successfully")
        
        # Run immediate catch-up on startup
        asyncio.create_task(catchup_missed_roi())
        
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        raise


def stop_scheduler():
    """Gracefully stop the scheduler"""
    try:
        scheduler.shutdown(wait=True)
        logger.info("🛑 Scheduler stopped gracefully")
    except Exception as e:
        logger.error(f"❌ Error stopping scheduler: {e}")
