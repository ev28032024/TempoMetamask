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
            - status: str
            - row_index: int (1-indexed, for updates)
        """
        worksheet = self._get_worksheet()
        all_values = worksheet.get_all_values()
        
        profiles = []
        
        # Skip header row (index 0), data starts at row 2 (index 1)
        for row_idx, row in enumerate(all_values[1:], start=2):
            try:
                serial_col = config.SHEET_SERIAL_NUMBER_COL
                status_col = config.SHEET_STATUS_COL
                
                if len(row) > serial_col and row[serial_col]:
                    serial_number = int(row[serial_col])
                    status = row[status_col] if len(row) > status_col else ""
                    
                    profiles.append({
                        'serial_number': serial_number,
                        'status': status,
                        'row_index': row_idx
                    })
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping row {row_idx}: {e}")
                continue
        
        logger.info(f"Found {len(profiles)} profiles in sheet")
        return profiles
    
    def get_pending_profiles(self) -> list[dict]:
        """Get profiles that need processing (status is empty or 'pending')."""
        all_profiles = self.get_all_profiles()
        
        pending = [
            p for p in all_profiles
            if not p['status'] or p['status'].lower() in ['pending', '']
        ]
        
        logger.info(f"Found {len(pending)} pending profiles")
        return pending
    
    def update_status(self, row_index: int, status: str, timestamp: bool = True) -> bool:
        """
        Update profile status in the sheet.
        
        Args:
            row_index: 1-indexed row number
            status: New status value
            timestamp: Whether to update timestamp column
        """
        try:
            worksheet = self._get_worksheet()
            
            # Update status column (1-indexed in gspread)
            status_col = config.SHEET_STATUS_COL + 1
            worksheet.update_cell(row_index, status_col, status)
            
            if timestamp:
                timestamp_col = config.SHEET_TIMESTAMP_COL + 1
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                worksheet.update_cell(row_index, timestamp_col, now)
            
            logger.info(f"Updated row {row_index}: status={status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update row {row_index}: {e}")
            return False
    
    def mark_in_progress(self, row_index: int) -> bool:
        """Mark profile as in progress."""
        return self.update_status(row_index, config.STATUS_IN_PROGRESS, timestamp=False)
    
    def mark_completed(self, row_index: int) -> bool:
        """Mark profile as completed."""
        return self.update_status(row_index, config.STATUS_COMPLETED)
    
    def mark_failed(self, row_index: int, error: str = None) -> bool:
        """Mark profile as failed."""
        status = config.STATUS_FAILED
        if error:
            status = f"{status}: {error[:50]}"
        return self.update_status(row_index, status)


def get_google_sheets_manager() -> GoogleSheetsManager:
    """Factory function to get configured Google Sheets manager."""
    return GoogleSheetsManager()
