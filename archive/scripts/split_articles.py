#!/usr/bin/env python3
"""
split_articles.py - Splits cleaned newspaper text into individual articles

Usage:
    python split_articles.py <date> [--aggressive-mode]
    
Example:
    python split_articles.py 1977-08-14
    python split_articles.py 1977-08-14 --aggressive-mode
"""

import re
import sys
import json
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
import unicodedata
import string
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('split_articles')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "archive"
PROCESSED_DIR = ARCHIVE_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
DATA_DIR = PROJECT_ROOT / "data"
INDEX_FILE = DATA_DIR / "index.json"

def ensure_directories():
    """Ensure necessary directories exist."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

def load_cleaned_text(date_str):
    """
    Load cleaned OCR text from file.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        str: Cleaned OCR text content
    """
    input_file = PROCESSED_DIR / f"{date_str}-clean.txt"
    
    if not input_file.exists():
        logger.error(f"Cleaned OCR file not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return f.read()

def detect_headlines(text, aggressive=False):
    """
    Detect potential headlines in the text.
    
    Args:
        text (str): Cleaned OCR text
        aggressive (bool): Whether to use aggressive headline detection
        
    Returns:
        list: List of (start_index, end_index, headline_text) tuples
    """
    headlines = []
    
    # Standard headline patterns
    all_caps_pattern = r'(?m)^[A-Z][A-Z0-9\s,\'":;.-]{10,80}$'
    title_case_pattern = r'(?m)^(?:[A-Z][a-z0-9]+\s+){2,}[A-Z][a-z0-9]+[.!?]?$'
    
    # Find all-caps headlines
    for match in re.finditer(all_caps_pattern, text):
        headline = match.group(0).strip()
        if len(headline.split()) >= 3 and len(headline) <= 100:
            headlines.append((match.start(), match.end(), headline))
    
    # Find title case headlines
    for match in re.finditer(title_case_pattern, text):
        headline = match.group(0).strip()
        if len(headline.split()) >= 3 and len(headline) <= 100:
            # Check if not already added as all-caps
            if not any(h[0] == match.start() for h in headlines):
                headlines.append((match.start(), match.end(), headline))
    
    # If in aggressive mode, add additional headline patterns
    if aggressive and len(headlines) < 5:
        logger.info("Using aggressive headline detection...")
        
        # Shorter all caps patterns (more likely to get false positives, but better than nothing)
        short_caps_pattern = r'(?m)^[A-Z][A-Z0-9\s,\'":;.-]{5,80}$'
        for match in re.finditer(short_caps_pattern, text):
            headline = match.group(0).strip()
            if len(headline.split()) >= 2 and len(headline) <= 100:
                # Check if not already added
                if not any(h[0] == match.start() for h in headlines):
                    headlines.append((match.start(), match.end(), headline))
        
        # Lines that start with capitalized words
        capitalized_start_pattern = r'(?m)^[A-Z][a-z0-9]+(?:\s+[A-Za-z][a-z0-9]+){1,6}[.!?]?$'
        for match in re.finditer(capitalized_start_pattern, text):
            headline = match.group(0).strip()
            if len(headline) >= 10 and len(headline) <= 100:
                # Check if not already added
                if not any(h[0] == match.start() for h in headlines):
                    headlines.append((match.start(), match.end(), headline))
        
        # Look for lines followed by paragraph breaks
        paragraph_break_pattern = r'(?m)^.{10,80}$(?:\s*\n){2,}'
        for match in re.finditer(paragraph_break_pattern, text):
            headline = match.group(0).split('\n')[0].strip()
            if len(headline) >= 10 and len(headline) <= 100:
                # Check if not already added
                if not any(abs(h[0] - match.start()) < 5 for h in headlines):
                    headlines.append((match.start(), match.start() + len(headline), headline))
    
    return headlines

def extract_articles(text, headlines, aggressive=False):
    """
    Extract articles from text based on detected headlines.
    
    Args:
        text (str): Cleaned OCR text
        headlines (list): List of (start_index, end_index, headline_text) tuples
        aggressive (bool): Whether to use aggressive article extraction
        
    Returns:
        list: List of dictionaries with article data
    """
    articles = []
    
    # If no headlines were found, create a fallback article
    if not headlines:
        if aggressive:
            logger.warning("No headlines found. Creating fallback articles by splitting the text.")
            
            # Split the text into chunks of roughly 1500 characters
            chunk_size = 1500
            chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
            
            for i, chunk in enumerate(chunks):
                # Skip very short chunks
                if len(chunk) < 100:
                    continue
                
                # Create a generic title from the first line or first few words
                title = ""
                first_line = chunk.split('\n', 1)[0].strip()
                if len(first_line) > 10 and len(first_line) < 80:
                    title = first_line
                else:
                    # Use first few words
                    words = chunk.split()[:8]
                    title = ' '.join(words) + '...'
                
                # Create article object
                article = {
                    "title": title,
                    "raw_text": chunk.strip()
                }
                
                articles.append(article)
            
            return articles
        else:
            # In non-aggressive mode, create a single article from the entire text
            # Get the first few words as a title
            words = text.split()[:8]
            title = ' '.join(words) + '...'
            
            article = {
                "title": title,
                "raw_text": text.strip()
            }
            
            articles.append(article)
            return articles
    
    # Sort headlines by start position
    headlines.sort(key=lambda x: x[0])
    
    # Iterate through headlines to extract articles
    for i, (start, end, headline) in enumerate(headlines):
        # Calculate the end of this article (start of next headline or end of text)
        article_end = headlines[i+1][0] if i+1 < len(headlines) else len(text)
        
        # Extract article text (skipping the headline itself)
        article_text = text[end:article_end].strip()
        
        # In standard mode, skip very short articles (likely false positives)
        # In aggressive mode, accept shorter articles
        min_length = 50 if aggressive else 100
        if len(article_text) < min_length:
            continue
        
        # Create article object
        article = {
            "title": headline,
            "raw_text": article_text.strip()
        }
        
        articles.append(article)
    
    return articles

def create_slug(title):
    """
    Create a URL-friendly slug from a title.
    
    Args:
        title (str): Article title
        
    Returns:
        str: URL-friendly slug
    """
    # Normalize unicode characters
    title = unicodedata.normalize('NFKD', title)
    
    # Convert to lowercase and remove punctuation
    title = ''.join(c for c in title if c in string.ascii_letters + string.digits + ' ')
    
    # Replace spaces with hyphens and limit length
    slug = '-'.join(title.lower().split())[:50]
    
    return slug

def save_articles(articles, date_str):
    """
    Save articles as individual JSON files.
    
    Args:
        articles (list): List of article dictionaries
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        list: List of saved article filenames
    """
    saved_files = []
    archive_id = get_archive_id(date_str)
    publication = os.getenv("DEFAULT_PUBLICATION", "Unknown")
    
    for i, article in enumerate(articles):
        # Create a slug from the title
        title_slug = create_slug(article["title"])
        if not title_slug:
            title_slug = f"article-{i+1}"
        
        # Prepare complete article data
        article_data = {
            "title": article["title"],
            "raw_text": article["raw_text"],
            "timestamp": date_str,
            "publication": publication,
            "source_issue": archive_id,
            "source_url": f"https://archive.org/details/{archive_id}"
        }
        
        # Save the article
        filename = f"{date_str}--{title_slug}.json"
        output_path = ARTICLES_DIR / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)
        
        saved_files.append(str(output_path))
    
    return saved_files

def get_archive_id(date_str):
    """Get archive ID from index file based on date."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index_data = json.load(f)
        
        for issue in index_data.get("processed_issues", []):
            if issue.get("date") == date_str:
                return issue.get("id", f"unknown-{date_str}")
    
    # Fallback if not found
    return f"san-antonio-express-news-{date_str}"

def update_index(date_str, article_files):
    """Update the index.json file with information about the processed articles."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index_data = json.load(f)
    else:
        logger.warning("Index file not found. Skipping index update.")
        return
    
    # Find the issue by date
    for issue in index_data.get("processed_issues", []):
        if issue.get("date") == date_str:
            issue["status"] = "processed"
            issue["article_count"] = len(article_files)
            issue["article_files"] = article_files
            issue["processed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    
    # Save updated index
    with open(INDEX_FILE, 'w') as f:
        json.dump(index_data, f, indent=2)

def verify_ocr_quality(text):
    """
    Verify OCR quality to determine if aggressive mode should be used.
    
    Args:
        text (str): Cleaned OCR text
        
    Returns:
        bool: True if OCR quality is good, False otherwise
    """
    # Check if text is too short
    if len(text) < 5000:
        logger.warning("OCR text is very short, likely low quality")
        return False
    
    # Check for paragraph structure
    paragraphs = re.split(r'\n\s*\n', text)
    if len(paragraphs) < 10:
        logger.warning("Few paragraph breaks detected, likely low quality OCR")
        return False
    
    # Check for reasonable paragraph lengths
    para_lengths = [len(p) for p in paragraphs if p.strip()]
    if para_lengths:
        avg_para_len = sum(para_lengths) / len(para_lengths)
        if avg_para_len < 50 or avg_para_len > 500:
            logger.warning(f"Unusual average paragraph length: {avg_para_len:.1f} chars")
            return False
    
    # Check for common OCR artifacts
    ocr_artifacts = r'[^\w\s,.;:!?\'"-]{4,}'
    artifact_matches = re.findall(ocr_artifacts, text)
    if len(artifact_matches) > len(text) / 1000:
        logger.warning("High number of OCR artifacts detected")
        return False
    
    # Check for sentence structure
    sentences = re.split(r'[.!?]+\s+', text)
    if len(sentences) < 20:
        logger.warning("Few sentence breaks detected, likely low quality OCR")
        return False
    
    return True

def main():
    """Main function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Split newspaper text into articles')
    parser.add_argument('date', help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--aggressive-mode', action='store_true', 
                       help='Use aggressive article splitting for poor quality OCR')
    args = parser.parse_args()
    
    date_str = args.date
    aggressive_mode = args.aggressive_mode
    
    ensure_directories()
    
    # Load cleaned text
    logger.info(f"Loading cleaned OCR text for date: {date_str}")
    cleaned_text = load_cleaned_text(date_str)
    
    # Check OCR quality and automatically enable aggressive mode if needed
    if not aggressive_mode:
        ocr_quality_good = verify_ocr_quality(cleaned_text)
        if not ocr_quality_good:
            logger.info("Poor OCR quality detected, automatically enabling aggressive mode")
            aggressive_mode = True
    
    # Detect headlines
    logger.info("Detecting headlines...")
    headlines = detect_headlines(cleaned_text, aggressive=aggressive_mode)
    logger.info(f"Found {len(headlines)} potential headlines")
    
    # If few headlines found in standard mode, try aggressive mode
    if len(headlines) < 5 and not aggressive_mode:
        logger.info("Few headlines detected, trying aggressive mode")
        aggressive_mode = True
        headlines = detect_headlines(cleaned_text, aggressive=True)
        logger.info(f"Found {len(headlines)} potential headlines in aggressive mode")
    
    # Extract articles
    logger.info("Extracting articles...")
    articles = extract_articles(cleaned_text, headlines, aggressive=aggressive_mode)
    logger.info(f"Extracted {len(articles)} articles")
    
    if not articles:
        logger.error("No articles were extracted! Creating a fallback article.")
        # Create a single fallback article
        articles = [{
            "title": f"Full text of {date_str} issue",
            "raw_text": cleaned_text
        }]
    
    # Save articles
    logger.info("Saving articles...")
    saved_files = save_articles(articles, date_str)
    
    # Update index
    update_index(date_str, saved_files)
    
    logger.info(f"Successfully saved {len(saved_files)} articles to: {ARTICLES_DIR}")
    # Print some sample headlines
    if articles:
        logger.info("Sample headlines:")
        for i, article in enumerate(articles[:5]):
            logger.info(f" - {article['title']}")
        if len(articles) > 5:
            logger.info(f" - ...and {len(articles) - 5} more")

if __name__ == "__main__":
    main() 