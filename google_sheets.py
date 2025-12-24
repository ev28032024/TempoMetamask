"""
Google Sheets integration for profile management
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]


class GoogleSheetsManager:
    """Manager for Google Sheets operations."""
    
    def __init__(self, sheet_id: str = None, credentials_path: str = None):
        self.sheet_id = sheet_id or config.GOOGLE_SHEET_ID
        self.credentials_path = credentials_path or config.GOOGLE_CREDENTIALS_PATH
        self._client = None
        self._sheet = None
        self._worksheet = None
    
    def _get_client(self) -> gspread.Client:
        """Get authenticated gspread client."""
        if self._client is None:
            creds_path = Path(self.credentials_path)
            
            if not creds_path.exists():
                raise FileNotFoundError(f"Credentials file not found: {creds_path}")
            
            credentials = Credentials.from_service_account_file(
                str(creds_path),
                scopes=SCOPES
            )
            
            self._client = gspread.authorize(credentials)
            logger.info("Google Sheets client authenticated successfully")
        
        return self._client
    
    def _get_worksheet(self) -> gspread.Worksheet:
        """Get the worksheet for profile data."""
        if self._worksheet is None:
            client = self._get_client()
            self._sheet = client.open_by_key(self.sheet_id)
            self._worksheet = self._sheet.worksheet(config.SHEET_NAME)
            logger.info(f"Connected to worksheet: {config.SHEET_NAME}")
        
        return self._worksheet
    
    def get_all_profiles(self) -> list[dict]:
        """
        Get all profiles from the sheet.
        
        Returns list of dicts with:
            - serial_number: int
            - add_funds_status: str
            - fee_token_status: str
            - gm_status: str
            - overall_status: str
            - row_index: int (1-indexed, for updates)
        """
        worksheet = self._get_worksheet()
        all_values = worksheet.get_all_values()
        
        profiles = []
        
        # Skip header row (index 0), data starts at row 2 (index 1)
        for row_idx, row in enumerate(all_values[1:], start=2):
            try:
                serial_col = config.SHEET_SERIAL_NUMBER_COL
                
                if len(row) > serial_col and row[serial_col]:
                    serial_number = int(row[serial_col])
                    
                    # Get status for each step
                    add_funds_status = row[config.SHEET_ADD_FUNDS_STATUS_COL] if len(row) > config.SHEET_ADD_FUNDS_STATUS_COL else ""
                    fee_token_status = row[config.SHEET_FEE_TOKEN_STATUS_COL] if len(row) > config.SHEET_FEE_TOKEN_STATUS_COL else ""
                    gm_status = row[config.SHEET_GM_STATUS_COL] if len(row) > config.SHEET_GM_STATUS_COL else ""
                    overall_status = row[config.SHEET_OVERALL_STATUS_COL] if len(row) > config.SHEET_OVERALL_STATUS_COL else ""
                    
                    profiles.append({
                        'serial_number': serial_number,
                        'add_funds_status': add_funds_status,
                        'fee_token_status': fee_token_status,
                        'gm_status': gm_status,
                        'overall_status': overall_status,
                        'row_index': row_idx
                    })
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping row {row_idx}: {e}")
                continue
        
        logger.info(f"Found {len(profiles)} profiles in sheet")
        return profiles
    
    def get_pending_profiles(self) -> list[dict]:
        """
        Get profiles that need processing.
        
        A profile is pending if:
        - Overall status is not 'Ready'
        - OR any step status is not 'OK'
        """
        all_profiles = self.get_all_profiles()
        
        pending = []
        for p in all_profiles:
            overall = p['overall_status'].strip().lower()
            
            # Profile is pending if not marked as Ready
            if overall != 'ready':
                pending.append(p)
        
        logger.info(f"Found {len(pending)} pending profiles")
        return pending
    
    def _update_cell(self, row_index: int, col_index: int, value: str) -> bool:
        """Update a single cell value."""
        try:
            worksheet = self._get_worksheet()
            # gspread uses 1-indexed columns
            worksheet.update_cell(row_index, col_index + 1, value)
            return True
        except Exception as e:
            logger.error(f"Failed to update cell ({row_index}, {col_index}): {e}")
            return False
    
    def update_add_funds_status(self, row_index: int, success: bool) -> bool:
        """Update Add Funds step status."""
        status = config.STATUS_OK if success else config.STATUS_FAILED
        result = self._update_cell(row_index, config.SHEET_ADD_FUNDS_STATUS_COL, status)
        logger.info(f"Row {row_index}: Add Funds = {status}")
        return result
    
    def update_fee_token_status(self, row_index: int, success: bool) -> bool:
        """Update Set fee token step status."""
        status = config.STATUS_OK if success else config.STATUS_FAILED
        result = self._update_cell(row_index, config.SHEET_FEE_TOKEN_STATUS_COL, status)
        logger.info(f"Row {row_index}: Fee Token = {status}")
        return result
    
    def update_gm_status(self, row_index: int, success: bool) -> bool:
        """Update GM transaction step status."""
        status = config.STATUS_OK if success else config.STATUS_FAILED
        result = self._update_cell(row_index, config.SHEET_GM_STATUS_COL, status)
        logger.info(f"Row {row_index}: GM = {status}")
        return result
    
    def update_overall_status(self, row_index: int, success: bool, error_msg: str = None) -> bool:
        """Update overall status."""
        if success:
            status = config.STATUS_READY
        else:
            status = f"{config.STATUS_ERROR}"
            if error_msg:
                status = f"{config.STATUS_ERROR}: {error_msg[:30]}"
        
        result = self._update_cell(row_index, config.SHEET_OVERALL_STATUS_COL, status)
        logger.info(f"Row {row_index}: Overall = {status}")
        return result
    
    def mark_completed(self, row_index: int) -> bool:
        """Mark profile as fully completed (Ready)."""
        return self.update_overall_status(row_index, success=True)
    
    def mark_failed(self, row_index: int, error: str = None) -> bool:
        """Mark profile as failed (Error)."""
        return self.update_overall_status(row_index, success=False, error_msg=error)


def get_google_sheets_manager() -> GoogleSheetsManager:
    """Factory function to get configured Google Sheets manager."""
    return GoogleSheetsManager()
