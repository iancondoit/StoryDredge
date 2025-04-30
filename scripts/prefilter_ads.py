#!/usr/bin/env python3
"""
prefilter_ads.py - Pre-filter likely ad articles before classification

Usage:
    python prefilter_ads.py <date>
    
Example:
    python prefilter_ads.py 1977-08-14
"""

import re
import sys
import json
import os
import logging
import argparse
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('prefilter')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
ADS_DIR = OUTPUT_DIR / "ads"

def ensure_directories():
    """Ensure necessary directories exist."""
    ADS_DIR.mkdir(parents=True, exist_ok=True)

def load_articles(date_str):
    """
    Load all article files for the given date.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        list: List of article file paths
    """
    article_files = list(ARTICLES_DIR.glob(f"{date_str}--*.json"))
    logger.info(f"Found {len(article_files)} article files for {date_str}")
    return article_files

def is_likely_ad(article_data):
    """
    Check if an article is likely an advertisement using heuristic rules.
    
    Args:
        article_data (dict): Article data from JSON file
        
    Returns:
        bool: True if likely an ad, False otherwise
        str: Reason for classification as ad
    """
    text = article_data.get("raw_text", "")
    title = article_data.get("title", "")
    
    # Common ad signals
    phone_pattern = r"\d{3}-\d{4}|\(\d{3}\)\s*\d{3}-\d{4}|\d{7}|\d{3}\s*\d{4}"
    price_pattern = r"\$\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*dollars"
    call_to_action = r"call today|call now|for information|limited time|special offer|apply now|inquire"
    realty_patterns = r"realty|realtor|real estate|property|home for sale|bedroom|bath|sq ft|acres"
    classified_patterns = r"for sale|help wanted|services|wanted"
    
    # Check length (most news articles aren't this short)
    if len(text) < 300:
        return True, "Short text length"
    
    # Check for multiple phone numbers (common in ads)
    phone_matches = re.findall(phone_pattern, text, re.IGNORECASE)
    if len(phone_matches) >= 2:
        return True, "Multiple phone numbers"
    
    # Check for prices (common in ads)
    price_matches = re.findall(price_pattern, text, re.IGNORECASE)
    if len(price_matches) >= 2:
        return True, "Multiple price mentions"
    
    # Check for calls to action (common in ads)
    if re.search(call_to_action, text, re.IGNORECASE):
        return True, "Contains call to action"
    
    # Strong indicators in title
    if re.search(r"(?:FOR SALE|HELP WANTED|SERVICES)", title, re.IGNORECASE):
        return True, "Ad-like title"
    
    # Check for real estate specific content
    if re.search(realty_patterns, text, re.IGNORECASE) and re.search(phone_pattern, text, re.IGNORECASE):
        return True, "Real estate content with contact info"
    
    # Check for classified ad patterns
    if re.search(classified_patterns, text, re.IGNORECASE) and len(text) < 1000:
        return True, "Classified ad pattern"
        
    return False, ""

def process_articles(article_files):
    """
    Process articles to identify likely advertisements.
    
    Args:
        article_files (list): List of article file paths
        
    Returns:
        tuple: (news_count, ad_count, news_files, ad_files)
    """
    news_count = 0
    ad_count = 0
    news_files = []
    ad_files = []
    
    for file_path in tqdm(article_files, desc="Pre-filtering articles"):
        # Load the article
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
        
        # Check if it's likely an ad
        is_ad, reason = is_likely_ad(article_data)
        
        if is_ad:
            ad_count += 1
            ad_files.append(file_path)
            
            # Optionally save to ads directory with metadata
            if ADS_DIR:
                article_data["detected_ad"] = True
                article_data["ad_detection_reason"] = reason
                ad_output_path = ADS_DIR / file_path.name
                
                with open(ad_output_path, 'w', encoding='utf-8') as f:
                    json.dump(article_data, f, indent=2)
        else:
            news_count += 1
            news_files.append(file_path)
    
    return news_count, ad_count, news_files, ad_files

def save_report(date_str, news_count, ad_count, news_files):
    """
    Save a processing report with statistics.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        news_count (int): Number of detected news articles
        ad_count (int): Number of detected ad articles
        news_files (list): List of news article file paths
    """
    report = {
        "date": date_str,
        "total_articles": news_count + ad_count,
        "news_articles": news_count,
        "ad_articles": ad_count,
        "news_percentage": round((news_count / (news_count + ad_count)) * 100, 2) if (news_count + ad_count) > 0 else 0,
        "news_files": [str(f.name) for f in news_files]
    }
    
    report_path = OUTPUT_DIR / f"prefilter_report_{date_str}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Report saved to {report_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python prefilter_ads.py <date>")
        print("Example: python prefilter_ads.py 1977-08-14")
        sys.exit(1)
    
    date_str = sys.argv[1]
    ensure_directories()
    
    # Load and process articles
    article_files = load_articles(date_str)
    news_count, ad_count, news_files, ad_files = process_articles(article_files)
    
    # Save the report
    save_report(date_str, news_count, ad_count, news_files)
    
    # Print summary
    logger.info(f"Processed {news_count + ad_count} articles")
    logger.info(f"Identified {news_count} news articles ({round((news_count / (news_count + ad_count)) * 100, 2)}%)")
    logger.info(f"Identified {ad_count} ad articles ({round((ad_count / (news_count + ad_count)) * 100, 2)}%)")
    
    # Create an articles list file for the classification step
    news_list_path = OUTPUT_DIR / f"news_files_{date_str}.txt"
    with open(news_list_path, 'w', encoding='utf-8') as f:
        for file_path in news_files:
            f.write(f"{file_path}\n")
    
    logger.info(f"News file list saved to {news_list_path}")
    logger.info(f"Next step: Run classify_articles.py with --file-list {news_list_path}")

if __name__ == "__main__":
    main() 