from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from aiogram import Bot

from app.db import get_session
from app.services import process_weekly_roi, list_users
from app.config import settings


scheduler = AsyncIOScheduler()


async def job_weekly_roi():
	with get_session() as session:
		processed = process_weekly_roi(session)
		_ = processed


async def job_daily_ping():
	# Send daily countdown messages to all users
	bot = Bot(token=settings.user_bot_token)
	with get_session() as session:
		users = list_users(session)
		for user in users:
			remaining_days = 0
			if user.next_roi_date:
				remaining_days = max(0, (user.next_roi_date.date() - datetime.utcnow().date()).days)
			text = (
				f"🌞 Good Morning!\n\n"
				f"💼 Balance: {user.current_balance:.2f}\n"
				f"📈 ROI Cycle: {user.roi_cycles_completed} / {settings.max_roi_cycles}\n"
				f"⏳ Next ROI in: {remaining_days} days"
			)
			try:
				await bot.send_message(chat_id=user.user_id, text=text)
			except Exception:
				# Ignore send failures (user blocked bot, etc.)
				pass


def setup_jobs():
	# Run weekly ROI check every day at 00:10 to catch due users
	scheduler.add_job(job_weekly_roi, "cron", hour=0, minute=10)
	# Daily user countdown message at 08:00
	scheduler.add_job(job_daily_ping, "cron", hour=8, minute=0)


def start_scheduler():
	setup_jobs()
	scheduler.start()
