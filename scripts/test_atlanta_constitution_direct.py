#!/usr/bin/env python3
"""
Test Atlanta Constitution Download (Direct Method)

This script tests downloading OCR files from the Atlanta Constitution collection directly
using curl with redirect following, then processes them through the pipeline.
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct_test")

# Issue IDs to test - using 2 default test issues
DEFAULT_TEST_ISSUES = [
    "per_atlanta-constitution_1922-01-01_54_203",
    "per_atlanta-constitution_1922-01-02_54_204"
]

def download_ocr_with_curl(issue_id: str, output_dir: Path) -> Optional[Path]:
    """
    Download OCR file using curl with redirect following.
    
    Args:
        issue_id: The archive.org identifier
        output_dir: Directory to save the downloaded file
        
    Returns:
        Path to the downloaded file or None if download failed
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{issue_id}.txt"
    
    url = f"https://archive.org/download/{issue_id}/{issue_id}_djvu.txt"
    logger.info(f"Downloading {issue_id} from {url}")
    
    try:
        # Run curl command with redirect following
        result = subprocess.run(
            ["curl", "-L", "-s", "-o", str(output_file), url],
            check=True
        )
        
        # Check if file exists and has content
        if output_file.exists() and output_file.stat().st_size > 0:
            logger.info(f"Successfully downloaded {issue_id} ({output_file.stat().st_size} bytes)")
            return output_file
        else:
            logger.error(f"Download completed but file is empty or missing: {output_file}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download {issue_id}: {e}")
        return None


def process_ocr_file(ocr_file: Path, issue_id: str) -> bool:
    """
    Process the downloaded OCR file through the pipeline components.
    
    Args:
        ocr_file: Path to the OCR file
        issue_id: The archive.org identifier
        
    Returns:
        True if processing successful, False otherwise
    """
    try:
        # Set up paths
        output_dir = Path("output") / issue_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy the OCR file to the raw.txt location expected by the pipeline
        raw_file = output_dir / "raw.txt"
        with open(ocr_file, 'rb') as src, open(raw_file, 'wb') as dst:
            dst.write(src.read())
        
        logger.info(f"Copied OCR to {raw_file}")
        
        # Now run custom processing directly 
        # Import necessary components
        from src.cleaner.ocr_cleaner import OCRCleaner
        from src.splitter.article_splitter import ArticleSplitter
        
        # Clean the OCR text
        logger.info("Cleaning OCR text")
        with open(raw_file, 'r', encoding='utf-8', errors='replace') as f:
            raw_ocr = f.read()
        
        cleaner = OCRCleaner()
        cleaned_text = cleaner.clean_text(raw_ocr)
        
        # Save cleaned text
        cleaned_file = output_dir / "cleaned.txt"
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        logger.info(f"Saved cleaned OCR to {cleaned_file}")
        
        # Split into articles
        logger.info("Splitting OCR into articles")
        splitter = ArticleSplitter()
        headlines = splitter.detect_headlines(cleaned_text)
        articles = splitter.extract_articles(cleaned_text, headlines)
        
        # Save articles
        articles_dir = output_dir / "articles"
        articles_dir.mkdir(exist_ok=True)
        
        logger.info(f"Extracted {len(articles)} articles")
        for i, article in enumerate(articles):
            article_file = articles_dir / f"article_{i:04d}.json"
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(article, f, indent=2)
        
        # We'll consider the test successful if we got this far
        # Skip classification which requires Ollama
        logger.info(f"Successfully processed {issue_id} through cleaning and splitting")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {issue_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def load_issues_file(file_path: str) -> List[str]:
    """
    Load issues from a JSON file.
    
    Args:
        file_path: Path to the issues JSON file
        
    Returns:
        List of issue IDs
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "issues" in data:
            return data["issues"]
        elif isinstance(data, list):
            return data
        else:
            logger.error(f"Invalid issues file format in {file_path}")
            return []
    except Exception as e:
        logger.error(f"Error loading issues file {file_path}: {e}")
        return []


def main():
    """Main entry point for the script."""
    # Set up temporary directory for downloads
    temp_dir = Path("temp_downloads")
    temp_dir.mkdir(exist_ok=True)
    
    # Track results
    results = {
        "successful": [],
        "failed": []
    }
    
    # Determine which issues to process
    if len(sys.argv) > 1:
        # If argument provided, treat it as an issues file
        issues_file = sys.argv[1]
        TEST_ISSUES = load_issues_file(issues_file)
        logger.info(f"Loaded {len(TEST_ISSUES)} issues from {issues_file}")
    else:
        # Otherwise use the default test issues
        TEST_ISSUES = DEFAULT_TEST_ISSUES
        logger.info(f"Using {len(TEST_ISSUES)} default test issues")
    
    # Process each test issue
    for issue_id in TEST_ISSUES:
        logger.info(f"Processing issue: {issue_id}")
        
        # Download OCR
        ocr_file = download_ocr_with_curl(issue_id, temp_dir)
        if not ocr_file:
            logger.error(f"Failed to download {issue_id}")
            results["failed"].append(issue_id)
            continue
        
        # Process the file
        success = process_ocr_file(ocr_file, issue_id)
        if success:
            results["successful"].append(issue_id)
        else:
            results["failed"].append(issue_id)
    
    # Output results
    logger.info("Test completed:")
    logger.info(f"  Successful: {len(results['successful'])}")
    logger.info(f"  Failed: {len(results['failed'])}")
    
    if results["failed"]:
        logger.info(f"  Failed issues: {', '.join(results['failed'])}")
    
    # Save results to file
    with open("direct_test_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main() 