#!/usr/bin/env python3
"""
split_articles.py - Splits cleaned newspaper text into individual articles

Usage:
    python split_articles.py <date>
    
Example:
    python split_articles.py 1977-08-14
"""

import re
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import unicodedata
import string
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "archive" / "processed"
OUTPUT_DIR = BASE_DIR / "output" / "articles"
DATA_DIR = BASE_DIR / "data"
INDEX_FILE = DATA_DIR / "index.json"

def ensure_directories():
    """Ensure necessary directories exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        print(f"Error: Cleaned OCR file not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return f.read()

def detect_headlines(text):
    """
    Detect potential headlines in the text.
    
    Args:
        text (str): Cleaned OCR text
        
    Returns:
        list: List of (start_index, end_index, headline_text) tuples
    """
    headlines = []
    
    # Headlines are often ALL CAPS or Title Case
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
    
    return headlines

def extract_articles(text, headlines):
    """
    Extract articles from text based on detected headlines.
    
    Args:
        text (str): Cleaned OCR text
        headlines (list): List of (start_index, end_index, headline_text) tuples
        
    Returns:
        list: List of dictionaries with article data
    """
    articles = []
    
    # Sort headlines by start position
    headlines.sort(key=lambda x: x[0])
    
    # Iterate through headlines to extract articles
    for i, (start, end, headline) in enumerate(headlines):
        # Calculate the end of this article (start of next headline or end of text)
        article_end = headlines[i+1][0] if i+1 < len(headlines) else len(text)
        
        # Extract article text (skipping the headline itself)
        article_text = text[end:article_end].strip()
        
        # Skip very short articles (likely false positives)
        if len(article_text) < 100:
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
        output_path = OUTPUT_DIR / filename
        
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
        print("Error: Index file not found.")
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

def main():
    """Main function."""
    ensure_directories()
    
    if len(sys.argv) < 2:
        print("Usage: python split_articles.py <date>")
        print("Example: python split_articles.py 1977-08-14")
        return
    
    date_str = sys.argv[1]
    
    # Load cleaned text
    print(f"Loading cleaned OCR text for date: {date_str}")
    cleaned_text = load_cleaned_text(date_str)
    
    # Detect headlines
    print("Detecting headlines...")
    headlines = detect_headlines(cleaned_text)
    print(f"Found {len(headlines)} potential headlines")
    
    # Extract articles
    print("Extracting articles...")
    articles = extract_articles(cleaned_text, headlines)
    print(f"Extracted {len(articles)} articles")
    
    # Save articles
    print("Saving articles...")
    saved_files = save_articles(articles, date_str)
    
    # Update index
    update_index(date_str, saved_files)
    
    print(f"Successfully saved {len(saved_files)} articles to: {OUTPUT_DIR}")
    # Print some sample headlines
    if articles:
        print("\nSample headlines:")
        for i, article in enumerate(articles[:5]):
            print(f" - {article['title']}")
        if len(articles) > 5:
            print(f" - ...and {len(articles) - 5} more")

if __name__ == "__main__":
    main() 