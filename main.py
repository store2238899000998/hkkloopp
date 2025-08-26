from fastapi import FastAPI
import asyncio
from contextlib import asynccontextmanager

from app.db import init_db
from scheduler.jobs import start_scheduler
from bots.user_bot import run_user_bot
from bots.admin_bot import run_admin_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle"""
    print("🚀 Starting Investment Bot system...")

    # 1. Init database
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database init failed: {e}")

    # 2. Start scheduler
    try:
        start_scheduler()
        print("✅ Scheduler started")
    except Exception as e:
        print(f"❌ Scheduler failed: {e}")

    # 3. Start bots concurrently in background
    try:
        asyncio.create_task(run_user_bot())
        asyncio.create_task(run_admin_bot())
        print("🤖 Bots started (user + admin)")
    except Exception as e:
        print(f"❌ Bot startup error: {e}")

    yield  # 👉 FastAPI runs here

    # 4. Shutdown hooks (optional cleanup)
    print("🛑 Shutting down Investment Bot system...")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello from Investment Bot API + Bots 🚀"}



