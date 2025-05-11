#!/usr/bin/env python3
"""
classify_articles.py - Use AI to classify articles and extract structured metadata

Usage:
    python classify_articles.py <date> [--section=<section>] [--file-list=<filepath>]
    
Example:
    python classify_articles.py 1977-08-14
    python classify_articles.py 1977-08-14 --section=news
    python classify_articles.py 1977-08-14 --file-list=output/news_files_1977-08-14.txt
"""

import os
import sys
import json
import logging
import argparse
import time
import concurrent.futures
import hashlib
import gzip
from datetime import datetime, timedelta
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

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
CLASSIFIED_DIR = OUTPUT_DIR / "classified"

# Default settings and API settings
DEFAULT_PUBLICATION = os.getenv("DEFAULT_PUBLICATION", "San Antonio Express-News")
API_KEY = os.getenv("OPENAI_API_KEY")
API_RATE_LIMIT = int(os.getenv("OPENAI_RATE_LIMIT", "20"))  # Requests per minute
BATCH_SIZE = 10  # Process this many articles in a single API call (increased from 5)
MAX_WORKERS = 4  # Number of concurrent API calls (increased from 3)
USE_CACHE = os.getenv("USE_API_CACHE", "true").lower() in ("true", "1", "yes")
CACHE_DIR = Path(os.getenv("API_CACHE_DIR", str(PROJECT_ROOT / "cache" / "api_responses")))
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", "30"))  # How long to keep cached responses

def ensure_directories():
    """Ensure necessary directories exist."""
    CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)
    if USE_CACHE:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

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

def load_articles_from_file_list(file_list_path):
    """
    Load articles from a file list (output of prefilter_ads.py)
    
    Args:
        file_list_path (Path): Path to the file containing article paths
        
    Returns:
        list: List of article dictionaries
    """
    articles = []
    
    if not file_list_path.exists():
        logger.error(f"File list not found: {file_list_path}")
        return []
    
    logger.info(f"Loading articles from file list: {file_list_path}")
    
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            file_paths = [Path(line.strip()) for line in f if line.strip()]
        
        for file_path in file_paths:
            if not file_path.exists():
                logger.warning(f"Article file not found: {file_path}")
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    
                # Add file path for reference
                article['file_path'] = str(file_path)
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error loading article {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error loading file list: {e}")
        
    logger.info(f"Loaded {len(articles)} articles from file list")
    return articles

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.call_times = []
        self.min_interval = 60.0 / calls_per_minute
    
    def wait_if_needed(self):
        """Wait if we've exceeded our rate limit."""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        # If at limit, wait until we can make another call
        if len(self.call_times) >= self.calls_per_minute:
            oldest_call = min(self.call_times)
            wait_time = 60 - (now - oldest_call)
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        # Always ensure minimum interval between calls
        if self.call_times and now - self.call_times[-1] < self.min_interval:
            wait_time = self.min_interval - (now - self.call_times[-1])
            time.sleep(wait_time)
        
        # Record this call
        self.call_times.append(time.time())

# Create a global rate limiter
rate_limiter = RateLimiter(API_RATE_LIMIT)

def generate_cache_key(article_batch):
    """Generate a cache key for a batch of articles."""
    if not USE_CACHE:
        return None
        
    # Create a deterministic representation of the batch
    content_str = ""
    for article in article_batch:
        # Use only the raw text and any potential unique identifiers
        content_str += article.get('raw_text', '')[:1000]  # First 1000 chars
        content_str += article.get('title', '')
        
    # Create a hash of the content
    key = hashlib.md5(content_str.encode('utf-8')).hexdigest()
    return key

def get_cached_response(cache_key):
    """Get a cached API response if it exists and is not expired."""
    if not USE_CACHE or not cache_key:
        return None
        
    cache_file = CACHE_DIR / f"{cache_key}.json.gz"
    
    if not cache_file.exists():
        return None
        
    # Check if cache is expired
    cache_stat = cache_file.stat()
    cache_time = datetime.fromtimestamp(cache_stat.st_mtime)
    if datetime.now() - cache_time > timedelta(days=CACHE_TTL_DAYS):
        # Cache expired
        cache_file.unlink()
        return None
        
    try:
        with gzip.open(cache_file, 'rt', encoding='utf-8') as f:
            cached_data = json.load(f)
        logger.info(f"Using cached response for {cache_key}")
        return cached_data
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        return None

def save_to_cache(cache_key, response_data):
    """Save an API response to the cache."""
    if not USE_CACHE or not cache_key:
        return
        
    cache_file = CACHE_DIR / f"{cache_key}.json.gz"
    
    try:
        with gzip.open(cache_file, 'wt', encoding='utf-8') as f:
            json.dump(response_data, f)
        logger.info(f"Saved response to cache: {cache_key}")
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")

def clean_cache():
    """Clean expired items from the cache."""
    if not USE_CACHE:
        return
        
    try:
        current_time = datetime.now()
        cache_files = list(CACHE_DIR.glob("*.json.gz"))
        
        expired_count = 0
        for cache_file in cache_files:
            cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if current_time - cache_time > timedelta(days=CACHE_TTL_DAYS):
                cache_file.unlink()
                expired_count += 1
                
        if expired_count > 0:
            logger.info(f"Cleaned {expired_count} expired items from cache")
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")

def classify_article_batch(article_batch):
    """
    Process a batch of articles with OpenAI to extract structured metadata
    
    Args:
        article_batch (list): List of article dictionaries
        
    Returns:
        list: Processed articles with metadata or None for errors
    """
    # Check cache first
    cache_key = generate_cache_key(article_batch)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        return cached_response
    
    # Apply rate limiting
    rate_limiter.wait_if_needed()
    
    # Prepare the batch prompt
    batch_prompt = """You are tasked with analyzing newspaper articles from historical archives to extract structured information.

For each of the following newspaper articles, carefully extract the actual headline, byline, dateline, and full content.
Don't use placeholders like 'ARTICLE 1' - instead, identify the ACTUAL headline from the text.

"""
    
    for i, article in enumerate(article_batch):
        batch_prompt += f"ARTICLE {i+1}:\n```\n{article['raw_text'][:1000]}... (truncated)\n```\n\n"
    
    batch_prompt += """
For each article, provide a JSON object with these fields:
- headline: Extract the actual title/headline of the article. Look for large text, capitalized phrases, or text that appears to be a title.
- byline: The author's name, if present (e.g., "By John Smith").
- dateline: Location and date information, if present (e.g., "SAN ANTONIO, AUG. 14 —").
- body: The main text of the article, cleaned of artifacts.
- section: Categorize as "news", "ad", "editorial", "classified", or "unknown".
- tags: An array of keywords related to the article content.

Format your response as a JSON array containing one object for each article, in the same order as provided.
"""
    
    data = {
        "model": "gpt-3.5-turbo-16k",  # Using a model with larger context
        "messages": [
            {"role": "system", "content": "You are a helpful assistant specialized in analyzing historical newspaper content. Return valid JSON with properly extracted article details."},
            {"role": "user", "content": batch_prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        # Make the API call directly with httpx
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            json=data,
            timeout=120.0  # Longer timeout for batch processing
        )
        
        logger.info(f"HTTP Request: {response.request.method} {response.request.url} {response.status_code} {response.reason_phrase!r}")
        
        # Check the response
        if response.status_code != 200:
            logger.error(f"API error: {response.status_code}, {response.text}")
            return [None] * len(article_batch)
        
        # Parse the response
        response_data = response.json()
        completion_text = response_data["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        try:
            # First try to parse directly
            try:
                metadata_list = json.loads(completion_text)
            except json.JSONDecodeError as json_err:
                # If that fails, try to clean up common escape sequence issues
                logger.warning(f"Initial JSON parsing failed: {json_err}")
                # Replace invalid escape sequences with their proper forms
                fixed_text = completion_text.replace('\\n', '\\\\n').replace('\\t', '\\\\t')
                # Handle any other invalid escape sequences by removing the backslash
                import re
                fixed_text = re.sub(r'\\([^"\\/bfnrtu])', r'\1', fixed_text)
                
                try:
                    metadata_list = json.loads(fixed_text)
                    logger.info("Successfully parsed JSON after fixing escape sequences")
                except json.JSONDecodeError:
                    # If that still fails, try a more aggressive approach - extract the JSON structure manually
                    logger.warning("JSON parsing still failed after fixing escape sequences, trying manual extraction")
                    # Simple fallback: just process individual articles manually
                    metadata_list = []
                    for i, article in enumerate(article_batch):
                        # Create a basic metadata dict for each article
                        metadata = {
                            "headline": f"Untitled Article {i+1}",
                            "body": article.get('raw_text', '')[:500] + "... (truncated)",
                            "section": "unknown",
                            "tags": []
                        }
                        metadata_list.append(metadata)
            
            # Handle both array and object responses
            if isinstance(metadata_list, dict) and "articles" in metadata_list:
                metadata_list = metadata_list["articles"]
            elif isinstance(metadata_list, dict):
                # Single article response
                metadata_list = [metadata_list]
                
            # Ensure we have the right number of results
            if len(metadata_list) != len(article_batch):
                logger.warning(f"Expected {len(article_batch)} results, got {len(metadata_list)}")
                # Pad with None if needed
                if len(metadata_list) < len(article_batch):
                    metadata_list.extend([None] * (len(article_batch) - len(metadata_list)))
                else:
                    metadata_list = metadata_list[:len(article_batch)]
            
            # Merge with original metadata
            results = []
            for i, metadata in enumerate(metadata_list):
                if metadata is None:
                    results.append(None)
                    continue
                    
                article = article_batch[i]
                result = {
                    **metadata,
                    "timestamp": article.get("timestamp", ""),
                    "publication": article.get("publication", DEFAULT_PUBLICATION),
                    "source_issue": article.get("source_issue", ""),
                    "source_url": article.get("source_url", "")
                }
                results.append(result)
            
            # Save to cache
            if USE_CACHE and cache_key:
                save_to_cache(cache_key, results)
                
            return results
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {e}")
            logger.error(f"Response text: {completion_text}")
            return [None] * len(article_batch)
        
    except Exception as e:
        logger.error(f"Error classifying article batch: {e}")
        return [None] * len(article_batch)

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
    
    # Split articles into batches
    article_batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
    logger.info(f"Processing {len(articles)} articles in {len(article_batches)} batches")
    
    # Create a ThreadPoolExecutor for parallel processing
    results = []
    total_batches = len(article_batches)
    
    with tqdm(total=len(articles), desc="Classifying articles") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_batch_idx = {
                executor.submit(classify_article_batch, batch): i 
                for i, batch in enumerate(article_batches)
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_batch_idx):
                batch_idx = future_to_batch_idx[future]
                current_batch = article_batches[batch_idx]
                
                try:
                    batch_results = future.result()
                    
                    # Process and save each result in the batch
                    for j, result in enumerate(batch_results):
                        article_idx = batch_idx * BATCH_SIZE + j
                        if article_idx >= len(articles):
                            break
                            
                        article = articles[article_idx]
                        
                        if result is None:
                            errors += 1
                            pbar.update(1)
                            continue
                        
                        # Track section counts
                        section = result.get('section', 'unknown')
                        section_counts[section] = section_counts.get(section, 0) + 1
                        
                        # Skip if doesn't match section filter
                        if section_filter and section != section_filter:
                            pbar.update(1)
                            continue
                            
                        # Save the result
                        original_path = Path(article['file_path'])
                        file_name = original_path.name
                        output_path = output_dir / file_name
                        
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                            
                        processed_count += 1
                        pbar.update(1)
                        
                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx}: {e}")
                    errors += len(current_batch)
                    pbar.update(len(current_batch))
    
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
    """Main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Classify newspaper articles using OpenAI')
    parser.add_argument('date', help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--section', help='Filter by section type')
    parser.add_argument('--file-list', help='Path to a list of article files to process')
    parser.add_argument('--batch-size', type=int, help='Number of articles to process in each API call')
    parser.add_argument('--max-workers', type=int, help='Number of concurrent API calls')
    parser.add_argument('--no-cache', action='store_true', help='Disable API response caching')
    parser.add_argument('--clean-cache', action='store_true', help='Clean expired cache items')
    args = parser.parse_args()
    
    date = args.date
    section_filter = args.section
    file_list = args.file_list
    
    # Update batch size and max workers if provided
    global BATCH_SIZE, MAX_WORKERS, USE_CACHE
    if args.batch_size:
        BATCH_SIZE = args.batch_size
    if args.max_workers:
        MAX_WORKERS = args.max_workers
    if args.no_cache:
        USE_CACHE = False
    
    logger.info(f"Using batch size: {BATCH_SIZE}, max workers: {MAX_WORKERS}, cache enabled: {USE_CACHE}")
    
    # Clean cache if requested
    if args.clean_cache:
        clean_cache()
    
    # Load articles
    if file_list:
        file_list_path = Path(file_list)
        articles = load_articles_from_file_list(file_list_path)
    else:
        articles = load_articles_from_directory(ARTICLES_DIR, date_filter=date)
    
    if not articles:
        logger.error("No articles to process")
        sys.exit(1)
    
    # Ensure directories exist
    ensure_directories()
    
    # Create a date-specific classified directory
    date_dir = CLASSIFIED_DIR / date
    date_dir.mkdir(parents=True, exist_ok=True)
    
    # Process articles
    processed_count, section_counts = process_articles(
        articles, date_dir, section_filter=section_filter
    )
    
    logger.info(f"Processed {processed_count} articles")
    for section, count in section_counts.items():
        logger.info(f"  {section}: {count}")
    
    # Save report
    save_report(date, processed_count, section_counts, date_dir)
    
    logger.info("Classification complete!")

if __name__ == "__main__":
    main() 