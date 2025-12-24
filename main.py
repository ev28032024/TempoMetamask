"""
Tempo Testnet Automation - Main Entry Point

Automates interactions with Tempo Testnet:
1. Connects MetaMask to Tempo Faucet
2. Adds Tempo network
3. Requests test tokens (Add Funds)
4. Sets fee token
5. Performs GM transaction on onchaingm.com
"""
import sys
import time
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
            profile_data: Dict with serial_number, statuses, row_index
            
        Returns:
            True if successful, False otherwise
        """
        serial_number = profile_data['serial_number']
        row_index = profile_data['row_index']
        
        logger.info(f"Processing profile {serial_number} (row {row_index})")
        
        driver = None
        user_id = None
        all_steps_success = True
        
        try:
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
            
            # Check if steps need to be executed based on current status
            need_add_funds = profile_data.get('add_funds_status', '').upper() != 'OK'
            need_fee_token = profile_data.get('fee_token_status', '').upper() != 'OK'
            need_gm = profile_data.get('gm_status', '').upper() != 'OK'
            
            # Run Tempo Faucet automation
            faucet = TempoFaucetAutomation(driver, metamask)
            
            # Step 1: Navigate to faucet and connect MetaMask
            if need_add_funds or need_fee_token:
                logger.info("Starting Tempo Faucet automation...")
                
                if not faucet.navigate_to_faucet():
                    raise Exception("Failed to navigate to faucet")
                
                if not faucet.connect_metamask():
                    raise Exception("Failed to connect MetaMask")
                
                if not faucet.add_tempo_network():
                    logger.warning("Failed to add Tempo network, continuing...")
                
                # Step 2: Add Funds
                if need_add_funds:
                    add_funds_success = faucet.request_faucet_funds()
                    self.sheets.update_add_funds_status(row_index, add_funds_success)
                    if not add_funds_success:
                        all_steps_success = False
                        logger.error("Add Funds step failed")
                
                time.sleep(2)
                
                # Step 3: Set Fee Token
                if need_fee_token:
                    fee_token_success = faucet.set_fee_token()
                    self.sheets.update_fee_token_status(row_index, fee_token_success)
                    if not fee_token_success:
                        all_steps_success = False
                        logger.error("Set Fee Token step failed")
            
            time.sleep(2)
            
            # Step 4: GM Transaction
            if need_gm:
                logger.info("Starting GM Transaction automation...")
                gm = GMTransactionAutomation(driver, metamask)
                
                gm_success = gm.run_full_flow()
                self.sheets.update_gm_status(row_index, gm_success)
                if not gm_success:
                    all_steps_success = False
                    logger.error("GM Transaction step failed")
            
            # Update overall status
            if all_steps_success:
                self.sheets.mark_completed(row_index)
                logger.info(f"Profile {serial_number} completed successfully")
            else:
                self.sheets.mark_failed(row_index, "Some steps failed")
                logger.warning(f"Profile {serial_number} completed with errors")
            
            return all_steps_success
            
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
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all profiles regardless of status'
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
    elif args.all:
        # Process all profiles
        profiles = sheets.get_all_profiles()
    else:
        # Get pending profiles (not Ready)
        profiles = sheets.get_pending_profiles()
    
    if not profiles:
        logger.info("No profiles to process")
        return
    
    logger.info(f"Found {len(profiles)} profile(s) to process")
    
    if args.dry_run:
        logger.info("DRY RUN - Profiles to process:")
        for p in profiles:
            logger.info(
                f"  - Serial: {p['serial_number']}, Row: {p['row_index']}, "
                f"AddFunds: {p.get('add_funds_status', '-')}, "
                f"FeeToken: {p.get('fee_token_status', '-')}, "
                f"GM: {p.get('gm_status', '-')}, "
                f"Overall: {p.get('overall_status', '-')}"
            )
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
