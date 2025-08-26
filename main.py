from __future__ import annotations

import asyncio
import sys
import uvicorn
from multiprocessing import Process

from app.db import init_db
from scheduler.jobs import start_scheduler
from bots.user_bot import run_user_bot
from bots.admin_bot import run_admin_bot


async def start_bots_and_scheduler():
	"""Start both bots and the scheduler"""
	print("🚀 Starting Investment Bot System...")
	
	# Initialize database
	print("📊 Initializing database...")
	init_db()
	print("✅ Database initialized")
	
	# Start scheduler
	print("⏰ Starting scheduler...")
	start_scheduler()
	print("✅ Scheduler started")
	
	# Start both bots concurrently
	print("🤖 Starting Telegram bots...")
	try:
		await asyncio.gather(
			run_user_bot(),
			run_admin_bot(),
		)
	except KeyboardInterrupt:
		print("\n🛑 Shutting down bots...")
	except Exception as e:
		print(f"❌ Error starting bots: {e}")


def start_api():
	"""Start the FastAPI service"""
	print("🌐 Starting FastAPI server...")
	uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


def start_all():
	"""Start everything: API, bots, and scheduler"""
	print("🎯 Starting complete Investment Bot system...")
	
	# Start API in a separate process
	api_process = Process(target=start_api)
	api_process.start()
	print("✅ API started on http://localhost:8000")
	
	# Start bots and scheduler in main process
	try:
		asyncio.run(start_bots_and_scheduler())
	except KeyboardInterrupt:
		print("\n🛑 Shutting down...")
		api_process.terminate()
		api_process.join()
		print("✅ All services stopped")


if __name__ == "__main__":
	if len(sys.argv) > 1:
		command = sys.argv[1].lower()
		
		if command == "api":
			print("🌐 Starting API only...")
			start_api()
		elif command == "bots":
			print("🤖 Starting bots and scheduler only...")
			asyncio.run(start_bots_and_scheduler())
		elif command == "all" or command == "start":
			start_all()
		else:
			print("""
🎯 Investment Bot - Usage Options:

python main.py          # Start bots + scheduler only
python main.py api      # Start API only  
python main.py bots     # Start bots + scheduler only
python main.py all      # Start everything (API + bots + scheduler)
python main.py start    # Same as 'all'

Examples:
  python main.py        # Quick start for development
  python main.py all    # Full production setup
""")
	else:
		# Default: start bots and scheduler only
		print("🤖 Starting bots and scheduler...")
		asyncio.run(start_bots_and_scheduler())


