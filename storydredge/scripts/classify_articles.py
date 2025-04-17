#!/usr/bin/env python3
"""
classify_articles.py - Uses OpenAI to extract structured metadata from articles

Usage:
    python classify_articles.py [date] [--filter=<section>]
    
Example:
    python classify_articles.py 1977-08-14
    python classify_articles.py 1977-08-14 --filter=news
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter
import glob
from dotenv import load_dotenv
from tqdm import tqdm
import openai

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
ARTICLES_DIR = BASE_DIR / "output" / "articles"
CLASSIFIED_DIR = BASE_DIR / "output" / "classified"
DATA_DIR = BASE_DIR / "data"

# OpenAI API settings
API_KEY = os.getenv("OPENAI_API_KEY")
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Valid section types
VALID_SECTIONS = ["news", "ad", "editorial", "classified", "unknown"]

def ensure_directories():
    """Ensure necessary directories exist."""
    CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)

def setup_openai():
    """Initialize the OpenAI client with the API key."""
    if not API_KEY:
        print("Error: OPENAI_API_KEY is not set in .env file")
        sys.exit(1)
    
    openai.api_key = API_KEY
    return openai.OpenAI(api_key=API_KEY)

def load_article_files(date_str=None):
    """
    Load all article files or filter by date.
    
    Args:
        date_str (str, optional): Date string in YYYY-MM-DD format
        
    Returns:
        list: List of article file paths
    """
    if date_str:
        pattern = f"{date_str}--*.json"
        files = list(ARTICLES_DIR.glob(pattern))
    else:
        files = list(ARTICLES_DIR.glob("**/*.json"))
    
    return files

def process_article(client, article_path):
    """
    Process a single article with OpenAI.
    
    Args:
        client: OpenAI client
        article_path (Path): Path to the article JSON file
        
    Returns:
        dict: Processed article data with metadata or None if failed
    """
    try:
        # Load the article
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
        
        # Skip if the article is very short (likely not a real article)
        if len(article.get("raw_text", "")) < 50:
            return None
        
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
{article["raw_text"]}
---
"""
        
        # Call OpenAI API with retries
        for attempt in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                # Extract and parse the JSON response
                try:
                    completion_text = response.choices[0].message.content
                    metadata = json.loads(completion_text)
                    
                    # Validate section value
                    if "section" in metadata and metadata["section"] not in VALID_SECTIONS:
                        metadata["section"] = "unknown"
                    
                    # Ensure tags is an array
                    if "tags" not in metadata or not isinstance(metadata["tags"], list):
                        metadata["tags"] = []
                    
                    # Merge with original metadata
                    result = {
                        **metadata,
                        "timestamp": article.get("timestamp", ""),
                        "publication": article.get("publication", ""),
                        "source_issue": article.get("source_issue", ""),
                        "source_url": article.get("source_url", "")
                    }
                    
                    return result
                
                except json.JSONDecodeError:
                    print(f"Error: Could not decode JSON from OpenAI response for {article_path.name}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        return None
            
            except (openai.RateLimitError, openai.APIError) as e:
                print(f"OpenAI API error: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (attempt + 1)  # Exponential backoff
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"Failed to process {article_path.name} after {MAX_RETRIES} attempts")
                    return None
    
    except Exception as e:
        print(f"Error processing {article_path.name}: {str(e)}")
        return None

def save_classified_article(article_data, original_filename):
    """
    Save the classified article data to a JSON file.
    
    Args:
        article_data (dict): Processed article data
        original_filename (str): Original filename
        
    Returns:
        Path: Path to the saved file
    """
    # Create the output filename
    section = article_data.get("section", "unknown")
    
    # Extract the date part and slug
    parts = original_filename.stem.split("--", 1)
    date_str = parts[0]
    
    if len(parts) > 1:
        slug = parts[1]
    else:
        slug = "article"
    
    # Create a new filename with section
    new_filename = f"{date_str}--{section}--{slug}.json"
    output_path = CLASSIFIED_DIR / new_filename
    
    # Save the file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, indent=2, ensure_ascii=False)
    
    return output_path

def filter_articles(articles, section_filter):
    """
    Filter articles by section.
    
    Args:
        articles (list): List of processed articles
        section_filter (str): Section to filter by
        
    Returns:
        list: Filtered list of articles
    """
    if not section_filter or section_filter.lower() == "all":
        return articles
    
    return [article for article in articles if article.get("section", "unknown").lower() == section_filter.lower()]

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Classify newspaper articles using OpenAI")
    parser.add_argument("date", nargs="?", help="Date in YYYY-MM-DD format (optional)")
    parser.add_argument("--filter", help="Filter by section type (news, ad, editorial, classified)")
    args = parser.parse_args()
    
    ensure_directories()
    client = setup_openai()
    
    # Load article files
    article_files = load_article_files(args.date)
    total_files = len(article_files)
    
    if total_files == 0:
        print(f"No articles found{' for date ' + args.date if args.date else ''}")
        return
    
    print(f"Found {total_files} articles{' for date ' + args.date if args.date else ''}")
    
    # Process articles
    results = []
    failures = 0
    section_counter = Counter()
    
    print("Processing articles...")
    for file_path in tqdm(article_files, total=total_files):
        result = process_article(client, file_path)
        
        if result:
            results.append(result)
            section_counter[result.get("section", "unknown")] += 1
            
            # Save the classified article
            save_classified_article(result, file_path)
        else:
            failures += 1
    
    # Filter results if needed
    if args.filter:
        filtered_results = filter_articles(results, args.filter)
        print(f"\nFiltered to {len(filtered_results)} {args.filter} articles")
    
    # Print report
    print("\n----- Classification Report -----")
    print(f"Total articles processed: {total_files}")
    print(f"Successfully classified: {len(results)}")
    print(f"Failed: {failures}")
    print("\nBreakdown by section:")
    for section, count in section_counter.most_common():
        print(f"  - {section}: {count} ({count/len(results)*100:.1f}%)")
    
    # Save report
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_processed": total_files,
        "successful": len(results),
        "failed": failures,
        "sections": {section: count for section, count in section_counter.items()}
    }
    
    report_date = args.date or "all"
    report_file = CLASSIFIED_DIR / f"report-{report_date}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to {report_file}")

if __name__ == "__main__":
    main() 