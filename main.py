"""
Tempo Testnet Automation - Main Entry Point

Automates interactions with Tempo Testnet:
1. Connects MetaMask to Tempo Faucet
2. Adds Tempo network
3. Requests test tokens
4. Sets fee token
5. Performs GM transaction on onchaingm.com
"""
import sys
import time
import asyncio
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import config
from adspower_api import AdsPowerAPI, get_adspower_api
from google_sheets import GoogleSheetsManager, get_google_sheets_manager
from metamask_helper import MetaMaskHelper
from tempo_faucet import TempoFaucetAutomation
from gm_transaction import GMTransactionAutomation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tempo_automation.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class ProfileProcessor:
    """Processes individual browser profiles."""
    
    def __init__(self, adspower: AdsPowerAPI, sheets: GoogleSheetsManager):
        self.adspower = adspower
        self.sheets = sheets
    
    def process_profile(self, profile_data: dict) -> bool:
        """
        Process a single profile through the complete automation flow.
        
        Args:
            profile_data: Dict with serial_number, status, row_index
            
        Returns:
            True if successful, False otherwise
        """
        serial_number = profile_data['serial_number']
        row_index = profile_data['row_index']
        
        logger.info(f"Processing profile {serial_number} (row {row_index})")
        
        driver = None
        user_id = None
        
        try:
            # Mark as in progress
            self.sheets.mark_in_progress(row_index)
            
            # Get profile info from AdsPower
            profile_info = self.adspower.get_profile_by_serial_number(serial_number)
            
            if not profile_info:
                raise Exception(f"Profile with serial_number {serial_number} not found in AdsPower")
            
            user_id = profile_info.get('user_id')
            logger.info(f"Found AdsPower profile: {user_id}")
            
            # Open browser
            browser_data = self.adspower.open_browser(user_id)
            time.sleep(3)  # Wait for browser to fully start
            
            # Get Selenium driver
            driver = self.adspower.get_selenium_driver(browser_data)
            
            # Initialize helpers
            metamask = MetaMaskHelper(driver)
            
            # Generate MetaMask password
            password = config.get_metamask_password(serial_number)
            logger.info(f"Using password pattern for profile {serial_number}")
            
            # Unlock MetaMask first (navigate to extension if needed)
            # Note: MetaMask should auto-open or we need to navigate to it
            
            # Run Tempo Faucet automation
            logger.info("Starting Tempo Faucet automation...")
            faucet = TempoFaucetAutomation(driver, metamask)
            
            if not faucet.run_full_flow():
                raise Exception("Tempo Faucet automation failed")
            
            time.sleep(2)
            
            # Run GM Transaction automation
            logger.info("Starting GM Transaction automation...")
            gm = GMTransactionAutomation(driver, metamask)
            
            if not gm.run_full_flow():
                raise Exception("GM Transaction automation failed")
            
            # Mark as completed
            self.sheets.mark_completed(row_index)
            logger.info(f"Profile {serial_number} completed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Profile {serial_number} failed: {e}")
            self.sheets.mark_failed(row_index, str(e))
            return False
            
        finally:
            # Cleanup
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            
            if user_id:
                try:
                    self.adspower.close_browser(user_id)
                except Exception:
                    pass


def process_profiles_parallel(profiles: list[dict], max_workers: int = 1) -> dict:
    """
    Process multiple profiles in parallel.
    
    Args:
        profiles: List of profile data dicts
        max_workers: Maximum concurrent profiles
        
    Returns:
        Dict with success and failure counts
    """
    adspower = get_adspower_api()
    sheets = get_google_sheets_manager()
    
    results = {
        'success': 0,
        'failed': 0,
        'total': len(profiles)
    }
    
    if max_workers > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            processor = ProfileProcessor(adspower, sheets)
            
            futures = {
                executor.submit(processor.process_profile, profile): profile
                for profile in profiles
            }
            
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    success = future.result()
                    if success:
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                except Exception as e:
                    logger.error(f"Profile {profile['serial_number']} error: {e}")
                    results['failed'] += 1
    else:
        # Sequential processing
        processor = ProfileProcessor(adspower, sheets)
        
        for profile in profiles:
            try:
                success = processor.process_profile(profile)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Profile {profile['serial_number']} error: {e}")
                results['failed'] += 1
            
            # Delay between profiles
            time.sleep(5)
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Tempo Testnet Automation - Faucet & GM Transactions'
    )
    
    parser.add_argument(
        '--profile', '-p',
        type=int,
        help='Process only specific profile by serial number'
    )
    
    parser.add_argument(
        '--parallel', '-n',
        type=int,
        default=config.MAX_PARALLEL_PROFILES,
        help=f'Number of profiles to process in parallel (default: {config.MAX_PARALLEL_PROFILES})'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List profiles to process without executing'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Tempo Testnet Automation Starting")
    logger.info("=" * 60)
    
    # Validate configuration
    errors = config.validate_config()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)
    
    # Check AdsPower connection
    adspower = get_adspower_api()
    if not adspower.check_connection():
        logger.error("Cannot connect to AdsPower. Is it running?")
        sys.exit(1)
    
    logger.info("AdsPower connection: OK")
    
    # Get profiles from Google Sheets
    sheets = get_google_sheets_manager()
    
    if args.profile:
        # Process specific profile
        all_profiles = sheets.get_all_profiles()
        profiles = [p for p in all_profiles if p['serial_number'] == args.profile]
        
        if not profiles:
            logger.error(f"Profile {args.profile} not found in Google Sheet")
            sys.exit(1)
    else:
        # Get pending profiles
        profiles = sheets.get_pending_profiles()
    
    if not profiles:
        logger.info("No profiles to process")
        return
    
    logger.info(f"Found {len(profiles)} profile(s) to process")
    
    if args.dry_run:
        logger.info("DRY RUN - Profiles to process:")
        for p in profiles:
            logger.info(f"  - Serial: {p['serial_number']}, Status: {p['status']}, Row: {p['row_index']}")
        return
    
    # Process profiles
    results = process_profiles_parallel(profiles, max_workers=args.parallel)
    
    logger.info("=" * 60)
    logger.info("Automation Complete")
    logger.info(f"  Total: {results['total']}")
    logger.info(f"  Success: {results['success']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
