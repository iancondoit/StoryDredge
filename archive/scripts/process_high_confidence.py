#!/usr/bin/env python3
"""
process_high_confidence.py - Optimized pipeline for processing newspapers at scale

This script combines the following steps into a single efficient pipeline:
1. Find high-confidence news articles
2. Classify only those articles with OpenAI
3. Extract structured data

Usage:
    python process_high_confidence.py <date> [--max-articles=<n>] [--batch-size=<n>] [--max-workers=<n>]
    
Example:
    python process_high_confidence.py 1977-08-14
    python process_high_confidence.py 1977-08-14 --max-articles=100 --batch-size=10 --max-workers=3
"""

import sys
import os
import json
import logging
import argparse
import subprocess
from pathlib import Path
import time
from datetime import datetime
from dotenv import load_dotenv
import concurrent.futures

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('process_high_confidence')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

def run_command(command, description, timeout=600):
    """Run a command with timeout and detailed logging."""
    logger.info(f"Running: {description}")
    logger.info(f"Command: {' '.join(command)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"Command completed successfully in {elapsed:.2f} seconds")
            return True
        else:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return False

def process_newspaper_issue(date_str, max_articles=None, batch_size=10, max_workers=3):
    """
    Process a newspaper issue with the optimized high-confidence pipeline.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        max_articles (int): Maximum number of news articles to process
        batch_size (int): Number of articles to process in each API call
        max_workers (int): Number of concurrent API calls to make
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Step 1: Find high-confidence news articles
    logger.info(f"Step 1: Finding high-confidence news articles for {date_str}")
    
    prefilter_command = [
        "python", str(SCRIPTS_DIR / "prefilter_news.py"),
        date_str
    ]
    
    if max_articles:
        prefilter_command.extend(["--max-articles", str(max_articles)])
    
    if not run_command(prefilter_command, "Pre-filtering for news articles", timeout=300):
        logger.error("Pre-filtering failed. Stopping pipeline.")
        return False
        
    # Check if news list file exists
    news_list_path = OUTPUT_DIR / f"high_confidence_news_{date_str}.txt"
    if not news_list_path.exists():
        logger.error(f"News list file not found: {news_list_path}")
        return False
    
    # Check the number of articles identified
    with open(news_list_path, 'r') as f:
        article_count = sum(1 for _ in f)
    
    logger.info(f"Found {article_count} high-confidence news articles")
    
    if article_count == 0:
        logger.warning("No high-confidence news articles found. Stopping pipeline.")
        return False
    
    # Step 2: Classify only high-confidence news articles
    logger.info(f"Step 2: Classifying {article_count} high-confidence news articles")
    
    classify_command = [
        "python", str(SCRIPTS_DIR / "classify_articles.py"),
        date_str,
        "--file-list", str(news_list_path),
        "--batch-size", str(batch_size),
        "--max-workers", str(max_workers)
    ]
    
    if not run_command(classify_command, "Classifying news articles", timeout=1800):
        logger.error("Classification failed. Stopping pipeline.")
        return False
    
    # Step 3: Generate report
    classified_dir = OUTPUT_DIR / "classified" / date_str
    report_path = classified_dir / f"report-{date_str}.json"
    
    if not report_path.exists():
        logger.warning(f"Classification report not found: {report_path}")
    else:
        try:
            with open(report_path, 'r') as f:
                report = json.load(f)
                
            logger.info("Classification results:")
            for section, count in report.get("section_counts", {}).items():
                logger.info(f"  {section}: {count}")
        except Exception as e:
            logger.error(f"Error reading classification report: {e}")
    
    # Record overall processing information
    processing_summary = {
        "date": date_str,
        "timestamp": datetime.now().isoformat(),
        "high_confidence_articles_found": article_count,
        "processed_successfully": True,
        "processing_time": time.time() - start_time
    }
    
    summary_path = OUTPUT_DIR / f"processing_summary_{date_str}.json"
    with open(summary_path, 'w') as f:
        json.dump(processing_summary, f, indent=2)
    
    logger.info(f"Processing summary saved to {summary_path}")
    logger.info(f"Processing completed successfully for {date_str}")
    
    return True

def process_batch_issues(dates, max_articles=None, batch_size=10, max_workers=3):
    """
    Process a batch of newspaper issues in parallel.
    
    Args:
        dates (list): List of dates to process (YYYY-MM-DD format)
        max_articles (int): Maximum number of news articles to identify per issue
        batch_size (int): Number of articles to process in each API call
        max_workers (int): Number of concurrent API calls
        
    Returns:
        dict: Results for each date
    """
    logger.info(f"Starting batch processing for {len(dates)} issues")
    results = {}
    
    # Process multiple issues in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all jobs
        future_to_date = {
            executor.submit(
                process_newspaper_issue, 
                date, 
                max_articles, 
                batch_size, 
                max_workers
            ): date for date in dates
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_date):
            date = future_to_date[future]
            try:
                success = future.result()
                results[date] = success
                if success:
                    logger.info(f"✅ Successfully processed issue: {date}")
                else:
                    logger.warning(f"❌ Failed to process issue: {date}")
            except Exception as e:
                logger.error(f"Error processing {date}: {e}")
                results[date] = False
    
    # Generate batch summary
    success_count = sum(1 for result in results.values() if result)
    
    batch_summary = {
        "timestamp": datetime.now().isoformat(),
        "total_issues": len(dates),
        "successful_issues": success_count,
        "failed_issues": len(dates) - success_count,
        "success_rate": round((success_count / len(dates)) * 100, 2) if dates else 0,
        "details": {date: {"success": success} for date, success in results.items()}
    }
    
    summary_path = OUTPUT_DIR / f"batch_processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_path, 'w') as f:
        json.dump(batch_summary, f, indent=2)
    
    logger.info(f"Batch processing summary saved to {summary_path}")
    
    return results

def main():
    """Main entry point"""
    global start_time
    start_time = time.time()
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Process newspaper issues with optimized pipeline')
    parser.add_argument('--dates', nargs='+', help='List of dates to process (YYYY-MM-DD)')
    parser.add_argument('--date-file', help='File containing dates to process (one per line)')
    parser.add_argument('--date', help='Single date to process (YYYY-MM-DD)')
    parser.add_argument('--max-articles', type=int, help='Maximum number of news articles to identify per issue')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of articles to process in each API call')
    parser.add_argument('--max-workers', type=int, default=3, help='Number of concurrent API calls')
    parser.add_argument('--parallel-issues', type=int, default=3, help='Number of issues to process in parallel')
    args = parser.parse_args()
    
    dates = []
    
    # Collect dates from various sources
    if args.date:
        dates.append(args.date)
        
    if args.dates:
        dates.extend(args.dates)
        
    if args.date_file:
        try:
            with open(args.date_file, 'r') as f:
                file_dates = [line.strip() for line in f if line.strip()]
                dates.extend(file_dates)
        except Exception as e:
            logger.error(f"Error reading date file: {e}")
            sys.exit(1)
    
    # Deduplicate dates
    dates = list(set(dates))
    
    if not dates:
        logger.error("No dates provided. Use --date, --dates, or --date-file")
        sys.exit(1)
    
    logger.info(f"Processing {len(dates)} newspaper issues")
    
    if len(dates) == 1:
        # Process a single issue
        logger.info(f"Processing single issue: {dates[0]}")
        success = process_newspaper_issue(
            dates[0],
            max_articles=args.max_articles,
            batch_size=args.batch_size,
            max_workers=args.max_workers
        )
        
        # Total processing time
        elapsed = time.time() - start_time
        logger.info(f"Total processing time: {elapsed:.2f} seconds")
        
        if not success:
            sys.exit(1)
    else:
        # Process multiple issues
        logger.info(f"Batch processing {len(dates)} issues with {args.parallel_issues} issues in parallel")
        
        if args.parallel_issues and args.parallel_issues > 1:
            # Process issues in parallel
            results = process_batch_issues(
                dates,
                max_articles=args.max_articles,
                batch_size=args.batch_size,
                max_workers=args.max_workers
            )
        else:
            # Process issues sequentially
            results = {}
            for date in dates:
                logger.info(f"Processing issue: {date}")
                success = process_newspaper_issue(
                    date,
                    max_articles=args.max_articles,
                    batch_size=args.batch_size,
                    max_workers=args.max_workers
                )
                results[date] = success
                
        # Total processing time
        elapsed = time.time() - start_time
        success_count = sum(1 for result in results.values() if result)
        
        logger.info(f"Batch processing completed in {elapsed:.2f} seconds")
        logger.info(f"Successfully processed {success_count}/{len(dates)} issues")
        
        if success_count < len(dates):
            sys.exit(1)

if __name__ == "__main__":
    main() 