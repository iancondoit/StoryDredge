#!/usr/bin/env python3
"""
test_batch.py - Run a small batch processing test to verify setup

Usage:
    python test_batch.py
"""

import os
import sys
import subprocess
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('test_batch')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEST_ISSUES_FILE = DATA_DIR / "test_issues.json"

def run_command(cmd, description, timeout=600):
    """Run a command with timeout and detailed logging."""
    logger.info(f"Starting {description}...")
    start_time = time.time()
    
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout  # Add timeout parameter
        )
        elapsed = time.time() - start_time
        logger.info(f"{description} completed in {elapsed:.2f} seconds")
        return True, result.stdout
    except subprocess.TimeoutExpired as e:
        logger.error(f"{description} timed out after {timeout} seconds")
        return False, f"Timeout: {e}"
    except subprocess.CalledProcessError as e:
        logger.error(f"{description} failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def run_setup():
    """Run the setup script to ensure environment is ready."""
    success, output = run_command(
        ["python", str(Path(__file__).parent / "setup.py")],
        "Setup script",
        timeout=60  # 60 seconds should be plenty for setup
    )
    
    if success:
        logger.info("Setup completed successfully")
    else:
        logger.error("Setup failed")
    
    return success

def run_batch_process():
    """Run batch processing on test issues."""
    # Add the --max-articles flag to limit processing time
    success, output = run_command(
        [
            "python", 
            str(Path(__file__).parent / "batch_process.py"),
            f"--issues={TEST_ISSUES_FILE}",
            "--max-articles=5",  # Reduced from 10 to 5 for faster testing
            "--skip-existing",
            "--skip-fetch"  # Skip fetching if files already exist
        ],
        "Batch processing",
        timeout=300  # 5 minutes timeout
    )
    
    if success:
        logger.info("Batch processing completed successfully")
    else:
        logger.error("Batch processing failed")
    
    return success

def check_results():
    """Check results of batch processing."""
    logger.info("Checking batch processing results...")
    
    # Check if output files were created
    output_dir = PROJECT_ROOT / "output"
    hsa_ready_dir = output_dir / "hsa-ready"
    
    issues_processed = 0
    articles_processed = 0
    
    # Use the test issues dates to check results
    for issue_date in ["1977-08-14", "1974-04-13"]:
        issue_dir = hsa_ready_dir / issue_date
        if issue_dir.exists():
            articles = list(issue_dir.glob("*.json"))
            article_count = len(articles)
            
            if article_count > 0:
                issues_processed += 1
                articles_processed += article_count
                logger.info(f"Found {article_count} processed articles for {issue_date}")
            else:
                logger.warning(f"No articles found for {issue_date}")
        else:
            logger.warning(f"No output directory found for {issue_date}")
            
            # Also check if the date is in YYYY/MM/DD format
            year = issue_date[:4]
            month = issue_date[5:7]
            day = issue_date[8:10]
            alt_path = hsa_ready_dir / year / month / day
            
            if alt_path.exists():
                articles = list(alt_path.glob("*.json"))
                article_count = len(articles)
                if article_count > 0:
                    issues_processed += 1
                    articles_processed += article_count
                    logger.info(f"Found {article_count} processed articles in {alt_path}")
    
    if issues_processed > 0:
        logger.info(f"Test successful: {issues_processed} issues and {articles_processed} articles processed")
        return True
    else:
        logger.error("Test failed: No issues were fully processed")
        # Check intermediate outputs to see where the process might have stopped
        logger.info("Checking intermediate outputs...")
        
        # Check if articles were split
        article_files = list((output_dir / "articles").glob("*.json"))
        if article_files:
            logger.info(f"Found {len(article_files)} article files in output/articles")
        else:
            logger.warning("No article files found in output/articles")
            
        # Check if ads were filtered
        ad_files = list((output_dir / "ads").glob("*.json"))
        if ad_files:
            logger.info(f"Found {len(ad_files)} ad files in output/ads")
        else:
            logger.warning("No ad files found in output/ads")
            
        # Check if articles were classified
        classified_files = list((output_dir / "classified").glob("**/*.json"))
        if classified_files:
            logger.info(f"Found {len(classified_files)} classified article files")
        else:
            logger.warning("No classified article files found")
            
        return False

def main():
    """Main function."""
    logger.info("Starting batch processing test...")
    
    # Make sure test issues file exists
    if not TEST_ISSUES_FILE.exists():
        logger.error(f"Test issues file not found: {TEST_ISSUES_FILE}")
        logger.info("Creating a test issues file...")
        
        # Create data directory if it doesn't exist
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create a simple test issues file
        test_issues = [
            {
                "archive_id": "san-antonio-express-news-1977-08-14",
                "date": "1977-08-14",
                "publication": "San Antonio Express-News"
            },
            {
                "archive_id": "chictrib-1974-04-13",
                "date": "1974-04-13",
                "publication": "Chicago Tribune"
            }
        ]
        
        import json
        with open(TEST_ISSUES_FILE, 'w') as f:
            json.dump(test_issues, f, indent=2)
        
        logger.info(f"Created test issues file: {TEST_ISSUES_FILE}")
    
    # Run setup
    if not run_setup():
        logger.error("Setup failed, stopping test")
        sys.exit(1)
    
    # Run batch process
    if not run_batch_process():
        logger.error("Batch processing failed, stopping test")
        sys.exit(1)
    
    # Check results
    if not check_results():
        logger.error("Results check failed")
        sys.exit(1)
    
    logger.info("All tests completed successfully!")

if __name__ == "__main__":
    main() 