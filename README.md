# Investment Telegram Bot (User + Admin) 

A neat, production-ready scaffold for a weekly ROI investment system with admin-controlled user creation, ROI scheduler, withdrawals restriction, reinvest flow, support tickets, and minimal API.

## Features
- Admin-only user creation and credits
- Weekly ROI (8% of initial balance, up to 4 cycles)
- Daily/weekly scheduler jobs (APScheduler)
- User bot: balance, withdraw gate, reinvest address, support, referral placeholder
- Admin bot: create users, credit balances
- FastAPI service: health, admin create user, list tickets, create support
- SQLAlchemy models and services

## Requirements
- Python 3.11+
- PostgreSQL (or update `DATABASE_URL` to your choice)

## Setup
1. Create virtualenv and install dependencies:
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```
2. Create `.env` file with your configuration:
```bash
USER_BOT_TOKEN=your_user_bot_token
ADMIN_BOT_TOKEN=your_admin_bot_token
ADMIN_CHAT_ID=your_telegram_id
DATABASE_URL=sqlite:///./local_investbot.db
SOL_ADDRESS=your_solana_address
USDT_TRC20_ADDRESS=your_trc20_address
USDT_ETH_ADDRESS=your_ethereum_address
BTC_ADDRESS=your_bitcoin_address
APP_NAME=InvestmentBot
ENV=development
TZ=UTC
```
3. Initialize database tables (auto on startup).

## 🚀 **Quick Start (Single Command)**

### **Option 1: Interactive Menu (Recommended)**
```bash
python start.py
```
This opens a beautiful menu where you can choose what to start!

### **Option 2: Direct Commands**
```bash
# Start everything (API + Bots + Scheduler)
python main.py all

# Start bots and scheduler only (for development)
python main.py

# Start API only
python main.py api

# Start bots only
python main.py bots
```

## 🎯 **Startup Options**

| Command | What It Starts | Use Case |
|---------|----------------|----------|
| `python start.py` | Interactive menu | **Best for beginners** |
| `python main.py all` | Everything | **Production setup** |
| `python main.py` | Bots + Scheduler | **Development** |
| `python main.py api` | FastAPI only | **API testing** |
| `python main.py bots` | Bots + Scheduler | **Bot testing** |

## 🌐 **Access Points**

- **API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`
- **User Bot**: Message your bot on Telegram
- **Admin Bot**: Message your admin bot on Telegram

## Railway Deployment 🚀

### Quick Deploy
1. **Fork/Clone** this repository to your GitHub
2. **Connect to Railway**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
3. **Set Environment Variables** in Railway dashboard:
   ```
   USER_BOT_TOKEN=your_user_bot_token
   ADMIN_BOT_TOKEN=your_admin_bot_token
   ADMIN_CHAT_ID=your_telegram_id
   DATABASE_URL=postgresql://... (Railway provides this)
   SOL_ADDRESS=your_solana_address
   USDT_TRC20_ADDRESS=your_trc20_address
   USDT_ETH_ADDRESS=your_ethereum_address
   BTC_ADDRESS=your_bitcoin_address
   ```
4. **Deploy** - Railway automatically detects and builds the project

### Railway Services
- **Web Service**: FastAPI API (auto-deploys from `railway.json`)
- **Worker Service**: Bots + Scheduler (deploy manually or via Procfile)

### Manual Worker Deployment
If you want to run the bots separately:
```bash
# In Railway terminal or via CLI
railway service create --name worker
railway run --service worker python main.py
```

## Admin Commands (Telegram)
- Click "Register New User" button for step-by-step registration
- `/credit <telegram_id> <amount>` - Credit user balance
- `/help` - Show admin help

## Notes
- Withdrawal approval path is a placeholder: user sees restriction until 4 cycles complete; after that, the bot indicates a request is sent to admin (manual processing for now).
- Daily countdown messages can be implemented in `scheduler/jobs.py` using stored users and sending via Bot API.
- For production, consider Redis/Celery for workers and robust logging.


