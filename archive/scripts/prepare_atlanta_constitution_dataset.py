#!/usr/bin/env python3
"""
Prepare Atlanta Constitution Dataset

This script prepares a test dataset from the Atlanta Constitution newspaper collection
on archive.org by:
1. Searching for issues in a specified date range
2. Checking OCR availability for each issue
3. Creating a batch processing file with issues that have OCR
4. Running a sample test to verify processing

The script follows the test-driven development approach by creating a reusable
utility for dataset preparation rather than a one-off script.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Any

# Ensure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher.archive_fetcher import ArchiveFetcher
from src.utils.progress import ProgressReporter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dataset_prep")


def parse_date(date_str: str) -> str:
    """
    Parse date string into YYYY-MM-DD format.
    Accepts various formats and normalizes to YYYY-MM-DD.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Normalized date string in YYYY-MM-DD format
    """
    formats_to_try = [
        "%Y-%m-%d",       # 1922-01-01
        "%Y/%m/%d",       # 1922/01/01
        "%m/%d/%Y",       # 01/01/1922
        "%m-%d-%Y",       # 01-01-1922
        "%d-%m-%Y",       # 01-01-1922
        "%B %d, %Y",      # January 1, 1922
        "%b %d, %Y"       # Jan 1, 1922
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")


def get_atlanta_constitution_issues(
    start_date: str,
    end_date: Optional[str] = None, 
    sample_size: int = 50
) -> List[Dict[str, Any]]:
    """
    Get Atlanta Constitution issues with OCR available in the specified date range.
    
    Args:
        start_date: Start date in any recognizable format (will be normalized)
        end_date: End date in any recognizable format (will be normalized)
        sample_size: Maximum number of issues to retrieve
        
    Returns:
        List of available issues with OCR
    """
    try:
        # Parse and validate dates
        normalized_start_date = parse_date(start_date)
        normalized_end_date = parse_date(end_date) if end_date else None
        
        date_range = (normalized_start_date, normalized_end_date) if normalized_end_date else (normalized_start_date, None)
        collection_id = "pub_atlanta-constitution"
        
        logger.info(f"Searching for Atlanta Constitution issues from {normalized_start_date}" + 
                   (f" to {normalized_end_date}" if normalized_end_date else ""))
        
        # Initialize the fetcher and search for issues
        fetcher = ArchiveFetcher()
        issues = fetcher.get_newspaper_issues(
            collection=collection_id,
            date_range=date_range,
            limit=sample_size
        )
        
        return issues
        
    except Exception as e:
        logger.error(f"Error getting Atlanta Constitution issues: {e}")
        return []


def prepare_dataset(
    start_date: str,
    end_date: Optional[str] = None,
    sample_size: int = 50,
    output_dir: str = "data/atlanta-constitution"
) -> Tuple[Path, List[Dict[str, Any]]]:
    """
    Prepare a dataset of Atlanta Constitution issues for testing.
    
    Args:
        start_date: Start date in any recognizable format
        end_date: End date in any recognizable format
        sample_size: Maximum number of issues to include
        output_dir: Directory to save the dataset
        
    Returns:
        Tuple of (path to issues file, list of issues)
    """
    # Get issues with OCR available
    issues = get_atlanta_constitution_issues(start_date, end_date, sample_size)
    
    if not issues:
        logger.error("No issues found with OCR available. Cannot prepare dataset.")
        return None, []
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    # Generate a filename that includes the date range
    start_date_str = parse_date(start_date).replace("-", "")
    end_date_str = parse_date(end_date).replace("-", "") if end_date else "present"
    
    issues_file = output_path / f"atlanta_constitution_{start_date_str}_to_{end_date_str}.json"
    
    # Save the issues file
    fetcher = ArchiveFetcher()
    issues_file_path = fetcher.save_issues_file(issues, issues_file)
    
    # Log some information about the dataset
    logger.info(f"Dataset prepared:")
    logger.info(f"  - Issues file: {issues_file_path}")
    logger.info(f"  - Total issues: {len(issues)}")
    
    earliest = min(issues, key=lambda x: x.get("date", "")) if issues else None
    latest = max(issues, key=lambda x: x.get("date", "")) if issues else None
    
    if earliest and latest:
        logger.info(f"  - Date range: {earliest.get('date', '').split('T')[0]} to {latest.get('date', '').split('T')[0]}")
    
    return issues_file_path, issues


def run_sample_test(issues_file: Path, num_issues: int = 1) -> bool:
    """
    Run a sample test on the first few issues to verify pipeline functionality.
    
    Args:
        issues_file: Path to the issues file
        num_issues: Number of issues to test
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        with open(issues_file, 'r') as f:
            data = json.load(f)
        
        issues = data.get("issues", [])
        if not issues:
            logger.error("No issues found in issues file.")
            return False
        
        # Take only the requested number of issues
        test_issues = issues[:num_issues]
        
        logger.info(f"Running sample test on {len(test_issues)} issues...")
        
        # Initialize the fetcher
        fetcher = ArchiveFetcher()
        
        # Test fetching each issue
        for issue_id in test_issues:
            logger.info(f"Testing fetch of issue: {issue_id}")
            
            # Fetch the issue
            result = fetcher.fetch_issue(issue_id)
            
            if result:
                logger.info(f"Successfully fetched issue: {issue_id}")
                # Count lines in the OCR file
                with open(result, 'r', encoding='utf-8', errors='replace') as f:
                    line_count = sum(1 for _ in f)
                logger.info(f"  - OCR file has {line_count} lines")
            else:
                logger.error(f"Failed to fetch issue: {issue_id}")
                return False
        
        logger.info("Sample test completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Error running sample test: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Prepare a test dataset from the Atlanta Constitution newspaper collection"
    )
    parser.add_argument("--start-date", required=True, 
                      help="Start date for issues (e.g., 1922-01-01)")
    parser.add_argument("--end-date", 
                      help="End date for issues (e.g., 1922-12-31)")
    parser.add_argument("--sample-size", type=int, default=50,
                      help="Maximum number of issues to include")
    parser.add_argument("--output-dir", default="data/atlanta-constitution",
                      help="Directory to save the dataset")
    parser.add_argument("--run-test", action="store_true",
                      help="Run a sample test on one issue after preparing the dataset")
    parser.add_argument("--test-issues", type=int, default=1,
                      help="Number of issues to test if --run-test is specified")
    
    args = parser.parse_args()
    
    # Prepare the dataset
    issues_file, issues = prepare_dataset(
        start_date=args.start_date,
        end_date=args.end_date,
        sample_size=args.sample_size,
        output_dir=args.output_dir
    )
    
    if not issues_file:
        sys.exit(1)
    
    # Run sample test if requested
    if args.run_test:
        success = run_sample_test(issues_file, args.test_issues)
        if not success:
            sys.exit(1)
    
    logger.info("Dataset preparation completed successfully.")


if __name__ == "__main__":
    main() 