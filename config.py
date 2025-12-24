"""
Configuration module for Tempo Testnet Automation
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.absolute()

# AdsPower Settings
ADSPOWER_API_URL = os.getenv("ADSPOWER_API_URL", "http://local.adspower.net:50325")
ADSPOWER_API_KEY = os.getenv("ADSPOWER_API_KEY", "")

# Google Sheets Settings
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json"))
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

# Sheet Column Configuration (0-indexed)
SHEET_SERIAL_NUMBER_COL = int(os.getenv("SHEET_SERIAL_NUMBER_COL", "0"))
SHEET_STATUS_COL = int(os.getenv("SHEET_STATUS_COL", "1"))
SHEET_TIMESTAMP_COL = int(os.getenv("SHEET_TIMESTAMP_COL", "2"))

# MetaMask Password Pattern
METAMASK_PASSWORD_PREFIX = os.getenv("METAMASK_PASSWORD_PREFIX", "ОткрываюМетамаск!")

# Parallelism
MAX_PARALLEL_PROFILES = int(os.getenv("MAX_PARALLEL_PROFILES", "1"))

# Timeouts (seconds)
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
ELEMENT_WAIT_TIMEOUT = int(os.getenv("ELEMENT_WAIT_TIMEOUT", "15"))
TRANSACTION_TIMEOUT = int(os.getenv("TRANSACTION_TIMEOUT", "60"))

# Target URLs
TEMPO_FAUCET_URL = "https://docs.tempo.xyz/quickstart/faucet"
ONCHAINGM_URL = "https://onchaingm.com/"

# Tempo Network Details
TEMPO_NETWORK_ID = "42429"
TEMPO_NETWORK_NAME = "Tempo Testnet"

# Statuses
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def get_metamask_password(serial_number: int) -> str:
    """Generate MetaMask password for given profile serial number."""
    return f"{METAMASK_PASSWORD_PREFIX}{serial_number}"


def validate_config() -> list[str]:
    """Validate configuration and return list of errors if any."""
    errors = []
    
    if not GOOGLE_SHEET_ID:
        errors.append("GOOGLE_SHEET_ID is not set")
    
    if not Path(GOOGLE_CREDENTIALS_PATH).exists():
        errors.append(f"Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}")
    
    return errors
