import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fillmypdf_email.db")

# Gmail API (OAuth, internal Workspace app) — see design doc section 7.1
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

SENDER_NAME = os.getenv("SENDER_NAME", "Riaz")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
PHYSICAL_ADDRESS = os.getenv("PHYSICAL_ADDRESS")

# Signs one-click unsubscribe tokens (design doc section 9)
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET")
UNSUBSCRIBE_BASE_URL = os.getenv("UNSUBSCRIBE_BASE_URL", "https://outreach.fillmypdf.com/u")

# Sending guardrails (design doc sections 3.3 and 6.1)
DAILY_CAP = int(os.getenv("DAILY_CAP", "40"))
MIN_SEND_SPACING_SECONDS = int(os.getenv("MIN_SEND_SPACING_SECONDS", "180"))
MAX_SEND_SPACING_SECONDS = int(os.getenv("MAX_SEND_SPACING_SECONDS", "420"))

# Global kill switch; flip to "true" to pause all sending immediately
KILL_SWITCH = os.getenv("KILL_SWITCH", "false").lower() == "true"
