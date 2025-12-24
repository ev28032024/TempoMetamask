"""
Configuration module for Tempo Testnet Automation
Loads settings from config.yaml
"""
import yaml
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_PATH = BASE_DIR / "config.yaml"

# Load configuration
def _load_config() -> dict:
    """Load configuration from YAML file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

_config = _load_config()

# AdsPower Settings
ADSPOWER_API_URL = _config['adspower']['api_url']
ADSPOWER_API_KEY = _config['adspower']['api_key']

# Google Sheets Settings
GOOGLE_SHEET_ID = _config['google_sheets']['sheet_id']
GOOGLE_CREDENTIALS_PATH = str(BASE_DIR / _config['google_sheets']['credentials_path'])
SHEET_NAME = _config['google_sheets']['sheet_name']

# Sheet Column Configuration (0-indexed)
SHEET_SERIAL_NUMBER_COL = _config['columns']['serial_number']
SHEET_ADDRESS_COL = _config['columns']['address']
SHEET_ADD_FUNDS_STATUS_COL = _config['columns']['add_funds_status']
SHEET_FEE_TOKEN_STATUS_COL = _config['columns']['fee_token_status']
SHEET_GM_STATUS_COL = _config['columns']['gm_status']
SHEET_OVERALL_STATUS_COL = _config['columns']['overall_status']

# MetaMask Password Pattern
METAMASK_PASSWORD_PREFIX = _config['metamask']['password_prefix']

# Parallelism
MAX_PARALLEL_PROFILES = _config['processing']['max_parallel_profiles']

# Timeouts (seconds)
PAGE_LOAD_TIMEOUT = _config['timeouts']['page_load']
ELEMENT_WAIT_TIMEOUT = _config['timeouts']['element_wait']
TRANSACTION_TIMEOUT = _config['timeouts']['transaction']

# Target URLs
TEMPO_FAUCET_URL = _config['urls']['tempo_faucet']
ONCHAINGM_URL = _config['urls']['onchaingm']

# Tempo Network Details
TEMPO_NETWORK_ID = _config['tempo_network']['id']
TEMPO_NETWORK_NAME = _config['tempo_network']['name']

# Statuses
STATUS_OK = _config['statuses']['ok']
STATUS_FAILED = _config['statuses']['failed']
STATUS_READY = _config['statuses']['ready']
STATUS_ERROR = _config['statuses']['error']


def get_metamask_password(serial_number: int) -> str:
    """Generate MetaMask password for given profile serial number."""
    return f"{METAMASK_PASSWORD_PREFIX}{serial_number}"


def validate_config() -> list[str]:
    """Validate configuration and return list of errors if any."""
    errors = []
    
    if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID == "YOUR_SHEET_ID_HERE":
        errors.append("google_sheets.sheet_id is not set in config.yaml")
    
    if not Path(GOOGLE_CREDENTIALS_PATH).exists():
        errors.append(f"Google credentials file not found: {GOOGLE_CREDENTIALS_PATH}")
    
    return errors
