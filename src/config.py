import os

from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str | None = None) -> str | None:
    """os.getenv, but an unset AND a blank ('KEY=') value both fall back to default."""
    value = os.getenv(key)
    return value if value else default


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DATABASE_URL = _env("DATABASE_URL", "sqlite:///./fillmypdf_email.db")

# "gmail" (design doc default, section 7) or "smtp" (generic, e.g. for testing
# from a Yahoo Mail mailbox before a Workspace mailbox is set up)
EMAIL_PROVIDER = _env("EMAIL_PROVIDER", "gmail").lower()

# Gmail API (OAuth, internal Workspace app) — see design doc section 7.1
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.getenv("GMAIL_REFRESH_TOKEN")

# Generic SMTP (used when EMAIL_PROVIDER=smtp)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(_env("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_SSL = _env("SMTP_USE_SSL", "false").lower() == "true"

SENDER_NAME = _env("SENDER_NAME", "Riaz")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
PHYSICAL_ADDRESS = os.getenv("PHYSICAL_ADDRESS")

# Signs one-click unsubscribe tokens (design doc section 9)
UNSUBSCRIBE_SECRET = os.getenv("UNSUBSCRIBE_SECRET")
UNSUBSCRIBE_BASE_URL = _env("UNSUBSCRIBE_BASE_URL", "https://outreach.fillmypdf.com/u")

# Sending guardrails (design doc sections 3.3 and 6.1)
DAILY_CAP = int(_env("DAILY_CAP", "40"))
MIN_SEND_SPACING_SECONDS = int(_env("MIN_SEND_SPACING_SECONDS", "180"))
MAX_SEND_SPACING_SECONDS = int(_env("MAX_SEND_SPACING_SECONDS", "420"))

# Global kill switch; flip to "true" to pause all sending immediately
KILL_SWITCH = _env("KILL_SWITCH", "false").lower() == "true"
