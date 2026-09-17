import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fillmypdf_email.db")

# "gmail" (design doc default, section 7) or "smtp" (generic, e.g. for testing
# from a Yahoo Mail mailbox before a Workspace mailbox is set up)
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail").lower()

# Gmail API (OAuth, internal Workspace app) — see design doc section 7.1
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

# Generic SMTP (used when EMAIL_PROVIDER=smtp)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"

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
