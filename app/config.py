from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
	app_name: str = os.getenv("APP_NAME", "InvestmentBot")
	env: str = os.getenv("ENV", "development")
	timezone: str = os.getenv("TZ", "UTC")

	# Telegram
	user_bot_token: str = os.getenv("USER_BOT_TOKEN", "")
	admin_bot_token: str = os.getenv("ADMIN_BOT_TOKEN", "")
	admin_chat_id: int = int(os.getenv("ADMIN_CHAT_ID", "0") or 0)

	# Database
	database_url: str = os.getenv(
		"DATABASE_URL",
		"sqlite+sqlite:///:memory:",
	)

	# Business config
	weekly_roi_percent: float = float(os.getenv("WEEKLY_ROI_PERCENT", "8"))
	max_roi_cycles: int = int(os.getenv("MAX_ROI_CYCLES", "4"))
	
	# Crypto addresses for reinvestment
	sol_address: str = os.getenv("SOL_ADDRESS", "")
	usdt_trc20_address: str = os.getenv("USDT_TRC20_ADDRESS", "")
	usdt_eth_address: str = os.getenv("USDT_ETH_ADDRESS", "")
	btc_address: str = os.getenv("BTC_ADDRESS", "")


settings = Settings()


