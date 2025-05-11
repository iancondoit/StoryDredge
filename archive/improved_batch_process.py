#!/usr/bin/env python3
"""
improved_batch_process.py - Enhanced batch processing of newspaper issues with robust ad filtering

Usage:
    python improved_batch_process.py --issues issues.json [options]

Options:
    --issues ISSUES         Path to JSON file with issues to process
    --max-articles INT      Maximum number of articles to process per issue (0 = all)
    --skip-fetch            Skip fetching step if files already exist
    --skip-existing         Skip issues that have already been processed
    --aggressive-splitting  Use aggressive article splitting for poor OCR quality
    --extra-ad-filtering    Apply extra rigorous ad filtering at all stages

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
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('improved_batch_process')

# Project paths - use consistent paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPT_DIR = PROJECT_ROOT / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "output"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
DATA_DIR = PROJECT_ROOT / "data"
METRICS_FILE = OUTPUT_DIR / "batch_metrics.json"
LOG_DIR = PROJECT_ROOT / "logs"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enhanced batch processing with improved filtering")
    parser.add_argument("--issues", required=True, help="Path to JSON file with issues to process")
    parser.add_argument("--max-articles", type=int, default=0, 
                        help="Maximum number of articles to process per issue (0 = all)")
    parser.add_argument("--skip-fetch", action="store_true", 
                        help="Skip fetching step if files already exist")
    parser.add_argument("--skip-existing", action="store_true", 
                        help="Skip issues that have already been processed")
    parser.add_argument("--aggressive-splitting", action="store_true",
                        help="Use aggressive article splitting for poor OCR quality")
    parser.add_argument("--extra-ad-filtering", action="store_true",
                        help="Apply extra rigorous ad filtering at all stages")
    parser.add_argument("--log-file", 
                        help="Path to log file (defaults to timestamped file in logs directory)")
    
    return parser.parse_args()

def setup_logging(log_file=None):
    """Set up logging with file output."""
    # Create logs directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create default log file name if not provided
    if not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"batch_process_{timestamp}.log"
    elif not Path(log_file).is_absolute():
        log_file = LOG_DIR / log_file
    
    # Add file handler to logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    logger.info(f"Logging to {log_file}")
    return log_file

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

def validate_processing_success(date_str, step_name):
    """Validate that a processing step created expected output files."""
    success = False
    
    if step_name == "fetch":
        success = (ARCHIVE_DIR / "raw" / f"{date_str}.txt").exists()
    elif step_name == "clean":
        success = (ARCHIVE_DIR / "cleaned" / f"{date_str}.txt").exists()
    elif step_name == "split":
        article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}-*.json"))
        if not article_files:
            article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}--*.json"))
        success = len(article_files) > 0
    elif step_name == "prefilter":
        success = (OUTPUT_DIR / f"news_files_{date_str}.txt").exists()
    elif step_name == "classify":
        success = (OUTPUT_DIR / "classified").glob(f"{date_str}*.json")
    elif step_name == "sanitize":
        success = any((OUTPUT_DIR / "classified").glob(f"**/{date_str}*.json"))
    elif step_name == "finalize":
        success = any((OUTPUT_DIR / "hsa-ready").glob(f"**/{date_str}*.json"))
    
    if not success:
        logger.warning(f"Validation failed for {step_name} step on {date_str}")
    
    return success

def run_command(cmd, check=True, error_msg="Command failed"):
    """Run a subprocess command with proper error handling."""
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"{error_msg}: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        if check:
            raise
        return None

def process_issue(issue, args):
    """Process a single newspaper issue through the pipeline with enhanced filtering."""
    archive_id = issue["archive_id"]
    date_str = issue["date"]
    publication = issue.get("publication", "Unknown")
    max_articles = args.max_articles
    skip_fetch = args.skip_fetch
    aggressive_splitting = args.aggressive_splitting
    extra_filtering = args.extra_ad_filtering
    
    metrics = {
        "archive_id": archive_id,
        "date": date_str,
        "publication": publication,
        "timestamps": {},
        "counts": {},
        "flags": {
            "aggressive_splitting": aggressive_splitting,
            "extra_filtering": extra_filtering
        }
    }
    
    logger.info(f"Processing issue: {archive_id} ({date_str})")
    
    # Step 1: Fetch the issue from archive.org
    start_time = time.time()
    
    if skip_fetch and (ARCHIVE_DIR / "raw" / f"{date_str}.txt").exists():
        logger.info(f"Skipping fetch for {date_str} (already exists)")
    else:
        logger.info(f"Fetching issue: {archive_id}")
        try:
            run_command(
                ["python", str(SCRIPT_DIR / "fetch_issue.py"), archive_id],
                error_msg=f"Error fetching issue {archive_id}"
            )
        except Exception as e:
            logger.error(f"Fatal error in fetch step: {e}")
            return None
    
    metrics["timestamps"]["fetch"] = time.time() - start_time
    
    # Validate fetch output
    if not validate_processing_success(date_str, "fetch"):
        logger.error(f"Failed to fetch {date_str}, skipping further processing")
        return None
    
    # Step 2: Clean and normalize OCR text
    start_time = time.time()
    logger.info(f"Cleaning and normalizing OCR text for {date_str}")
    try:
        run_command(
            ["python", str(SCRIPT_DIR / "clean_text.py"), date_str],
            error_msg=f"Error cleaning text for {date_str}"
        )
    except Exception as e:
        logger.error(f"Fatal error in clean step: {e}")
        return None
    
    metrics["timestamps"]["clean"] = time.time() - start_time
    
    # Validate clean output
    if not validate_processing_success(date_str, "clean"):
        logger.error(f"Failed to clean {date_str}, skipping further processing")
        return None
    
    # Step 3: Split into articles with optional aggressive mode
    start_time = time.time()
    logger.info(f"Splitting into articles for {date_str}" + 
                (" (aggressive mode)" if aggressive_splitting else ""))
    
    split_cmd = ["python", str(SCRIPT_DIR / "split_articles.py"), date_str]
    if aggressive_splitting:
        split_cmd.append("--aggressive-mode")
        
    try:
        run_command(
            split_cmd,
            error_msg=f"Error splitting articles for {date_str}"
        )
    except Exception as e:
        logger.error(f"Fatal error in split step: {e}")
        return None
    
    metrics["timestamps"]["split"] = time.time() - start_time
    
    # Get article count and validate
    article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}-*.json"))
    if not article_files:
        article_files = list((OUTPUT_DIR / "articles").glob(f"{date_str}--*.json"))
    
    article_count = len(article_files)
    metrics["counts"]["total_articles"] = article_count
    
    if article_count == 0:
        logger.error(f"No articles generated for {date_str}, skipping further processing")
        return None
    
    logger.info(f"Generated {article_count} articles for {date_str}")
    
    # Step 4: Pre-filter articles (news vs ads)
    start_time = time.time()
    logger.info(f"Pre-filtering news articles for {date_str}")
    
    prefilter_cmd = ["python", str(SCRIPT_DIR / "prefilter_news.py"), date_str]
    if max_articles > 0:
        prefilter_cmd.append(f"--max-articles={max_articles}")
    
    try:
        run_command(
            prefilter_cmd,
            error_msg=f"Error pre-filtering for {date_str}"
        )
    except Exception as e:
        logger.error(f"Fatal error in prefilter step: {e}")
        return None
    
    metrics["timestamps"]["prefilter"] = time.time() - start_time
    
    # Get prefilter stats
    prefilter_report_path = OUTPUT_DIR / f"news_prefilter_report_{date_str}.json"
    if prefilter_report_path.exists():
        try:
            with open(prefilter_report_path, 'r') as f:
                prefilter_data = json.load(f)
                metrics["counts"]["news_articles"] = prefilter_data.get("news_articles", 0)
                metrics["counts"]["other_articles"] = prefilter_data.get("other_articles", 0)
        except Exception as e:
            logger.warning(f"Could not read prefilter report: {e}")
    
    # Step 5: Classify articles with OpenAI
    start_time = time.time()
    logger.info(f"Classifying articles for {date_str}")
    
    try:
        news_file_path = OUTPUT_DIR / f"news_files_{date_str}.txt"
        if news_file_path.exists():
            classify_cmd = [
                "python", str(SCRIPT_DIR / "classify_articles.py"), 
                date_str, f"--file-list={news_file_path}"
            ]
            
            if extra_filtering:
                classify_cmd.append("--strict-ad-filtering")
                
            run_command(
                classify_cmd,
                error_msg=f"Error classifying articles for {date_str}"
            )
        else:
            logger.warning(f"No news files list found for {date_str}, classifying all articles")
            run_command(
                ["python", str(SCRIPT_DIR / "classify_articles.py"), date_str],
                error_msg=f"Error classifying all articles for {date_str}"
            )
    except Exception as e:
        logger.error(f"Fatal error in classify step: {e}")
        return None
    
    metrics["timestamps"]["classify"] = time.time() - start_time
    
    # Step 6: Migrate and sanitize
    start_time = time.time()
    logger.info(f"Migrating and sanitizing articles")
    try:
        run_command(
            ["python", str(SCRIPT_DIR / "migrate_and_sanitize.py")],
            error_msg=f"Error migrating and sanitizing articles"
        )
    except Exception as e:
        logger.error(f"Fatal error in migrate step: {e}")
        return None
    
    metrics["timestamps"]["sanitize"] = time.time() - start_time
    
    # Step 7: Filter and finalize
    start_time = time.time()
    logger.info(f"Filtering and finalizing for HSA")
    try:
        run_command(
            ["python", str(SCRIPT_DIR / "filter_and_finalize.py")],
            error_msg=f"Error filtering and finalizing"
        )
    except Exception as e:
        logger.error(f"Fatal error in finalize step: {e}")
        return None
        
    metrics["timestamps"]["finalize"] = time.time() - start_time
    
    # Step 8: Extra cleanup for HSA-ready directory if needed
    if extra_filtering:
        start_time = time.time()
        logger.info(f"Running extra ad cleanup for {date_str}")
        
        try:
            # Run our custom cleanup script
            run_command(
                ["python", str(PROJECT_ROOT / "cleanup_hsa_ready.py")],
                error_msg=f"Error running extra cleanup"
            )
        except Exception as e:
            logger.warning(f"Error in extra cleanup step (non-fatal): {e}")
        
        metrics["timestamps"]["extra_cleanup"] = time.time() - start_time
    
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
    logger.info(f"Result: {metrics['counts'].get('hsa_ready', 0)} articles ready for HSA")
    
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

def create_batch_summary(metrics_list, output_file):
    """Create a summary report of the batch processing."""
    if not metrics_list:
        logger.warning("No metrics to summarize")
        return
    
    total_issues = len(metrics_list)
    successful_issues = sum(1 for m in metrics_list if m.get("counts", {}).get("hsa_ready", 0) > 0)
    total_articles = sum(m.get("counts", {}).get("total_articles", 0) for m in metrics_list)
    hsa_ready_articles = sum(m.get("counts", {}).get("hsa_ready", 0) for m in metrics_list)
    
    total_time = sum(m.get("total_time", 0) for m in metrics_list)
    avg_time_per_issue = total_time / total_issues if total_issues > 0 else 0
    
    # Create summary object
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_issues": total_issues,
        "successful_issues": successful_issues,
        "success_rate": (successful_issues / total_issues) * 100 if total_issues > 0 else 0,
        "total_articles": total_articles,
        "hsa_ready_articles": hsa_ready_articles,
        "article_yield_rate": (hsa_ready_articles / total_articles) * 100 if total_articles > 0 else 0,
        "total_processing_time": total_time,
        "average_time_per_issue": avg_time_per_issue,
        "issues": [
            {
                "date": m.get("date"),
                "publication": m.get("publication"),
                "total_articles": m.get("counts", {}).get("total_articles", 0),
                "hsa_ready": m.get("counts", {}).get("hsa_ready", 0)
            }
            for m in metrics_list
        ]
    }
    
    # Save summary to file
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Batch processing summary saved to {output_file}")
    
    # Print summary to console
    logger.info(f"Batch processing completed in {total_time:.2f} seconds")
    logger.info(f"Successfully processed {successful_issues}/{total_issues} issues")
    logger.info(f"Total articles extracted: {total_articles}")
    logger.info(f"Articles ready for HSA: {hsa_ready_articles} ({summary['article_yield_rate']:.2f}%)")
    
    # List successful issues
    for issue in summary["issues"]:
        if issue["hsa_ready"] > 0:
            logger.info(f"Issue {issue['date']}: {issue['hsa_ready']} articles")

def main():
    """Main function."""
    args = parse_arguments()
    
    # Setup logging
    log_file = setup_logging(args.log_file)
    
    # Log start time and configuration
    start_time = time.time()
    logger.info("Starting improved batch processing")
    logger.info(f"Options: max_articles={args.max_articles}, skip_fetch={args.skip_fetch}, "
                f"aggressive_splitting={args.aggressive_splitting}, "
                f"extra_ad_filtering={args.extra_ad_filtering}")
    
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
        metrics = process_issue(issue, args)
        if metrics:
            metrics_list.append(metrics)
    
    # Generate timestamp for summary file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = OUTPUT_DIR / f"batch_processing_summary_{timestamp}.json"
    
    # Save metrics and create summary
    if metrics_list:
        save_metrics(metrics_list)
        create_batch_summary(metrics_list, summary_file)
    
    # Calculate and log total time
    total_time = time.time() - start_time
    logger.info(f"Batch processing completed in {total_time:.2f} seconds")
    logger.info(f"Successfully processed {len(metrics_list)}/{len(issues)} issues")
    logger.info(f"Log file: {log_file}")

if __name__ == "__main__":
    main() 