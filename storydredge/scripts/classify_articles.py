#!/usr/bin/env python3
"""
classify_articles.py - Use AI to classify articles and extract structured metadata
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx
from tqdm import tqdm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('classify')

# Load environment variables
load_dotenv()

# Default directories and API settings
DEFAULT_PUBLICATION = os.getenv("DEFAULT_PUBLICATION", "San Antonio Express-News")
API_KEY = os.getenv("OPENAI_API_KEY")

def load_articles_from_directory(articles_dir, date_filter=None, section_filter=None):
    """
    Load all article JSON files from the specified directory
    
    Args:
        articles_dir (Path): Directory containing article JSON files
        date_filter (str): Optional date to filter articles (YYYY-MM-DD)
        section_filter (str): Optional section type to filter by after classification
        
    Returns:
        list: List of article dictionaries
    """
    articles = []
    
    if not articles_dir.exists():
        logger.error(f"Articles directory not found: {articles_dir}")
        return []
    
    logger.info(f"Loading articles from {articles_dir}")
    
    # Get all JSON files in the directory
    article_files = list(articles_dir.glob("*.json"))
    
    if not article_files:
        logger.warning(f"No article files found in {articles_dir}")
        return []
    
    # Load each article
    for file_path in article_files:
        # Check if file matches date filter (e.g., 1977-08-14-article-123.json)
        if date_filter and date_filter not in file_path.stem:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                article = json.load(f)
                
            # Add file path for reference
            article['file_path'] = str(file_path)
            articles.append(article)
            
        except Exception as e:
            logger.error(f"Error loading article {file_path}: {e}")
    
    logger.info(f"Loaded {len(articles)} articles")
    return articles

def classify_article(article):
    """
    Process an article with OpenAI to extract structured metadata
    
    Args:
        article (dict): Article data with raw_text
        
    Returns:
        dict: Processed article with metadata or None if error
    """
    # Direct API call using httpx
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Prepare the prompt
    prompt = f"""
You are an expert in processing old newspaper articles. Given the raw OCR text of an article, extract structured metadata.

Return a JSON object with the following keys:

- headline (string): The title of the article.
- byline (string, optional): The name of the writer or editor.
- dateline (string, optional): A city and date header like "SAN ANTONIO, AUG. 14 —"
- body (string): The full cleaned article text.
- section (string): One of: "news", "ad", "editorial", "classified", "unknown".
- tags (array of strings): Optional keywords that describe the story.

Example input:
---
{article["raw_text"][:500]}... (truncated)
---
"""
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    try:
        # Make the API call directly with httpx
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60.0
        )
        
        # Check the response
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code}, {response.text}")
            return None
        
        # Parse the response
        response_data = response.json()
        completion_text = response_data["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        metadata = json.loads(completion_text)
        
        # Merge with original metadata
        result = {
            **metadata,
            "timestamp": article.get("timestamp", ""),
            "publication": article.get("publication", DEFAULT_PUBLICATION),
            "source_issue": article.get("source_issue", ""),
            "source_url": article.get("source_url", "")
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error classifying article: {e}")
        return None

def process_articles(articles, output_dir, section_filter=None):
    """
    Process a list of articles and save the results
    
    Args:
        articles (list): List of article dictionaries
        output_dir (Path): Directory to save processed articles
        section_filter (str): Optional section type to filter by
        
    Returns:
        tuple: (processed_count, section_counts)
    """
    processed_count = 0
    section_counts = {}
    errors = 0
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each article
    for article in tqdm(articles, desc="Classifying articles"):
        # Get the original file name
        original_path = Path(article['file_path'])
        file_name = original_path.name
        
        # Process the article
        result = classify_article(article)
        
        if result is None:
            errors += 1
            continue
        
        # Track section counts
        section = result.get('section', 'unknown')
        section_counts[section] = section_counts.get(section, 0) + 1
        
        # Skip if doesn't match section filter
        if section_filter and section != section_filter:
            continue
            
        # Save the result
        output_path = output_dir / file_name
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        processed_count += 1
        
    if errors > 0:
        logger.warning(f"{errors} articles failed to process")
            
    return processed_count, section_counts

def save_report(date, processed_count, section_counts, output_dir):
    """Save a processing report"""
    report = {
        "date": date,
        "processed_count": processed_count,
        "section_counts": section_counts,
        "timestamp": datetime.now().isoformat()
    }
    
    # Save report to output directory
    report_path = output_dir / f"report-{date}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Report saved to {report_path}")
    
    # Also save to parent directory
    parent_report_path = output_dir.parent / f"report-{date}.json"
    with open(parent_report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

def main():
    """Main function to run the script"""
    parser = argparse.ArgumentParser(description='Classify articles using OpenAI')
    parser.add_argument('date', help='Date in YYYY-MM-DD format')
    parser.add_argument('--filter', help='Filter by section type (news, ad, editorial, etc.)')
    args = parser.parse_args()
    
    if not API_KEY:
        logger.error("OPENAI_API_KEY not set in environment variables")
        sys.exit(1)
    
    # Set up paths
    date = args.date
    section_filter = args.filter
    
    articles_dir = Path(f"output/articles")
    output_dir = Path(f"output/classified")
    
    # Load and process articles
    articles = load_articles_from_directory(articles_dir, date_filter=date)
    
    if not articles:
        logger.error(f"No articles found for date {date}")
        sys.exit(1)
    
    logger.info(f"Processing {len(articles)} articles from {date}")
    
    # Process the articles
    processed_count, section_counts = process_articles(
        articles, 
        output_dir, 
        section_filter=section_filter
    )
    
    # Display results
    logger.info(f"Processed {processed_count} articles")
    
    for section, count in section_counts.items():
        logger.info(f"  {section}: {count} articles")
    
    if section_filter:
        logger.info(f"Filtered to {section_filter} articles only")
    
    # Save report
    save_report(date, processed_count, section_counts, output_dir)

if __name__ == "__main__":
    main() 