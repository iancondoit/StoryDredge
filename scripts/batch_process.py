#!/usr/bin/env python3
"""
batch_process.py - Process multiple newspaper issues in batch

Usage:
    python batch_process.py --issues issues.json
    python batch_process.py --issues issues.json --max-articles 100

Example issues.json format:
[
    {
        "archive_id": "san-antonio-express-news-1977-08-14",
        "date": "1977-08-14",
        "publication": "San Antonio Express-News"
    },
    ...
]
"""

import os
import sys
import json
import argparse
import subprocess
import time
from pathlib import Path
from datetime import datetime
import logging
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('batch_process')

# Project paths - use consistent paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "output"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
DATA_DIR = PROJECT_ROOT / "data"
METRICS_FILE = OUTPUT_DIR / "batch_metrics.json"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process multiple newspaper issues in batch")
    parser.add_argument("--issues", required=True, help="Path to JSON file with issues to process")
    parser.add_argument("--max-articles", type=int, default=0, 
                        help="Maximum number of articles to process per issue (0 = all)")
    parser.add_argument("--skip-fetch", action="store_true", 
                        help="Skip fetching step if files already exist")
    parser.add_argument("--skip-existing", action="store_true", 
                        help="Skip issues that have already been processed")
    
    return parser.parse_args()

def load_issues(file_path):
    """Load issues from JSON file."""
    # Handle both absolute paths and paths relative to the project root
    if not Path(file_path).is_absolute():
        file_path = PROJECT_ROOT / file_path
        
    try:
        with open(file_path, 'r') as f:
            issues = json.load(f)
        logger.info(f"Loaded {len(issues)} issues from {file_path}")
        return issues
    except Exception as e:
        logger.error(f"Error loading issues file: {e}")
        sys.exit(1)

def issue_already_processed(date_str):
    """Check if an issue has already been processed."""
    hsa_ready_dir = OUTPUT_DIR / "hsa-ready" / date_str
    return hsa_ready_dir.exists() and any(hsa_ready_dir.glob("*.json"))

def process_issue(issue, max_articles, skip_fetch=False):
    """Process a single newspaper issue through the pipeline."""
    archive_id = issue["archive_id"]
    date_str = issue["date"]
    publication = issue.get("publication", "Unknown")
    
    metrics = {
        "archive_id": archive_id,
        "date": date_str,
        "publication": publication,
        "timestamps": {},
        "counts": {}
    }
    
    logger.info(f"Processing issue: {archive_id} ({date_str})")
    
    # Step 1: Fetch the issue from archive.org
    start_time = time.time()
    
    if skip_fetch and (ARCHIVE_DIR / "raw" / f"{date_str}.txt").exists():
        logger.info(f"Skipping fetch for {date_str} (already exists)")
    else:
        logger.info(f"Fetching issue: {archive_id}")
        try:
            subprocess.run(
                ["python", str(SCRIPT_DIR / "fetch_issue.py"), archive_id],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Error fetching issue {archive_id}: {e}")
            return None
    
    metrics["timestamps"]["fetch"] = time.time() - start_time
    
    # Step 2: Clean and normalize OCR text
    start_time = time.time()
    logger.info(f"Cleaning and normalizing OCR text for {date_str}")
    try:
        subprocess.run(
            ["python", str(SCRIPT_DIR / "clean_text.py"), date_str],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error cleaning text for {date_str}: {e}")
        return None
    
    metrics["timestamps"]["clean"] = time.time() - start_time
    
    # Step 3: Split into articles
    start_time = time.time()
    logger.info(f"Splitting into articles for {date_str}")
    try:
        subprocess.run(
            ["python", str(SCRIPT_DIR / "split_articles.py"), date_str],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error splitting articles for {date_str}: {e}")
        return None
    
    metrics["timestamps"]["split"] = time.time() - start_time
    
    # Get article count
    article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}-*.json"))
    if not article_files:
        article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}--*.json"))
    article_count = len(article_files)
    metrics["counts"]["total_articles"] = article_count
    
    # Step 4: Pre-filter ads
    start_time = time.time()
    logger.info(f"Pre-filtering ads for {date_str}")
    try:
        subprocess.run(
            ["python", str(SCRIPT_DIR / "prefilter_ads.py"), date_str],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error pre-filtering ads for {date_str}: {e}")
        return None
    
    metrics["timestamps"]["prefilter"] = time.time() - start_time
    
    # Get prefilter stats
    prefilter_report_path = OUTPUT_DIR / f"prefilter_report_{date_str}.json"
    if prefilter_report_path.exists():
        with open(prefilter_report_path, 'r') as f:
            prefilter_data = json.load(f)
            metrics["counts"]["news_articles"] = prefilter_data.get("news_articles", 0)
            metrics["counts"]["ad_articles"] = prefilter_data.get("ad_articles", 0)
    
    # Step 5: Classify articles with OpenAI
    start_time = time.time()
    logger.info(f"Classifying articles for {date_str}")
    
    try:
        news_file_path = OUTPUT_DIR / f"news_files_{date_str}.txt"
        if news_file_path.exists():
            subprocess.run(
                ["python", str(SCRIPT_DIR / "classify_articles.py"), 
                 date_str, f"--file-list={news_file_path}"],
                check=True
            )
        else:
            subprocess.run(
                ["python", str(SCRIPT_DIR / "classify_articles.py"), date_str],
                check=True
            )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error classifying articles for {date_str}: {e}")
        return None
    
    metrics["timestamps"]["classify"] = time.time() - start_time
    
    # Step 6: Migrate and sanitize
    start_time = time.time()
    logger.info(f"Migrating and sanitizing articles")
    try:
        subprocess.run(
            ["python", str(SCRIPT_DIR / "migrate_and_sanitize.py")],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error migrating and sanitizing articles: {e}")
        return None
    
    metrics["timestamps"]["sanitize"] = time.time() - start_time
    
    # Step 7: Filter and finalize
    start_time = time.time()
    logger.info(f"Filtering and finalizing for HSA")
    try:
        subprocess.run(
            ["python", str(SCRIPT_DIR / "filter_and_finalize.py")],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error filtering and finalizing: {e}")
        return None
        
    metrics["timestamps"]["finalize"] = time.time() - start_time
    
    # Get final statistics
    hsa_ready_dir = OUTPUT_DIR / "hsa-ready" / date_str
    if hsa_ready_dir.exists():
        metrics["counts"]["hsa_ready"] = len(list(hsa_ready_dir.glob("*.json")))
    
    rejected_dir = OUTPUT_DIR / "rejected" / date_str
    if rejected_dir.exists():
        metrics["counts"]["rejected"] = len(list(rejected_dir.glob("*.json")))
    
    # Calculate total processing time
    metrics["total_time"] = sum(metrics["timestamps"].values())
    
    logger.info(f"Completed processing {date_str} in {metrics['total_time']:.2f} seconds")
    return metrics

def save_metrics(metrics_list):
    """Save processing metrics to a JSON file."""
    # Load existing metrics if available
    existing_metrics = []
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, 'r') as f:
                existing_metrics = json.load(f)
        except Exception:
            pass
    
    # Add new metrics
    all_metrics = existing_metrics + metrics_list
    
    # Save updated metrics
    with open(METRICS_FILE, 'w') as f:
        json.dump(all_metrics, f, indent=2)
    
    logger.info(f"Saved metrics to {METRICS_FILE}")

def main():
    """Main function."""
    args = parse_arguments()
    
    # Load issues from JSON file
    issues = load_issues(args.issues)
    
    # Create necessary directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process each issue
    metrics_list = []
    for issue in tqdm(issues, desc="Processing issues"):
        date_str = issue["date"]
        
        # Skip processed issues if requested
        if args.skip_existing and issue_already_processed(date_str):
            logger.info(f"Skipping {date_str} (already processed)")
            continue
        
        # Process the issue
        metrics = process_issue(issue, args.max_articles, args.skip_fetch)
        if metrics:
            metrics_list.append(metrics)
    
    # Save metrics
    if metrics_list:
        save_metrics(metrics_list)
    
    logger.info(f"Batch processing complete: {len(metrics_list)} issues processed")

if __name__ == "__main__":
    main() 