#!/usr/bin/env python3
"""
prefilter_news.py - AGGRESSIVELY pre-filter to identify only high-confidence news articles

Usage:
    python prefilter_news.py <date> [--max-articles=<n>]
    
Example:
    python prefilter_news.py 1977-08-14
    python prefilter_news.py 1977-08-14 --max-articles=100
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
logger = logging.getLogger('prefilter_news')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles"
NEWS_DIR = OUTPUT_DIR / "news_candidates"

def ensure_directories():
    """Ensure necessary directories exist."""
    NEWS_DIR.mkdir(parents=True, exist_ok=True)

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

def has_likely_news_structure(text):
    """Check if text has structural elements common in news articles."""
    # Check for dateline pattern (e.g., "WASHINGTON, May 14 -")
    dateline_pattern = r'[A-Z]{2,}(?:,\s*[A-Za-z]+\.?\s+\d{1,2}(?:st|nd|rd|th)?)?(?:\s*[-—–]|\s*\([A-Z]+\))'
    has_dateline = bool(re.search(dateline_pattern, text[:300]))
    
    # Check for paragraph structure (multiple paragraphs with reasonable length)
    paragraphs = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
    has_paragraphs = len(paragraphs) >= 3
    
    # Check average paragraph length
    if has_paragraphs:
        avg_para_len = sum(len(p) for p in paragraphs) / len(paragraphs)
        has_reasonable_para_length = 20 <= avg_para_len <= 300
    else:
        has_reasonable_para_length = False
    
    return has_dateline or (has_paragraphs and has_reasonable_para_length)

def is_likely_news(article_data):
    """
    Check if an article is likely a news article using heuristic rules.
    
    Args:
        article_data (dict): Article data from JSON file
        
    Returns:
        bool: True if likely news, False otherwise
        str: Reason for classification as news
    """
    text = article_data.get("raw_text", "")
    title = article_data.get("title", "")
    
    # Too short to be a news article
    if len(text) < 500:
        return False, "Too short"
        
    # Too long for most ads
    if len(text) > 8000:
        # Very long texts are more likely to be news articles
        long_text_bonus = 1
    else:
        long_text_bonus = 0
    
    # Header/title analysis
    has_news_title = False
    news_title_patterns = [
        r"(?:PROBE|INVESTIGATION|OFFICIALS|GOVERNMENT|REPORTS|ANNOUNCES|STUDY)",
        r"(?:CRISIS|AGREEMENT|DECISION|STATEMENT|CONFERENCE|MEETING|ELECTION|VOTE)",
        r"(?:DEBATE|TESTIMONY|HEARING|COUNCIL|COMMISSION|COMMITTEE|BOARD)"
    ]
    
    for pattern in news_title_patterns:
        if title and re.search(pattern, title, re.IGNORECASE):
            has_news_title = True
            break
    
    # Ad signals - expanded
    ad_patterns = [
        r"\d{3}-\d{4}",  # phone numbers
        r"\$\d+",  # prices
        r"call today|call now|for information|apply now",  # calls to action
        r"for sale|help wanted|services offered",  # classified headers
        r"[0-9]+%\s*off",  # sales discounts
        r"(?:real estate|realtor|realty|bedroom|bath|sq\.?\s*ft|lot size)",  # real estate
        r"limited time offer|special price|discount|sale ends|save now|buy now",  # marketing phrases
        r"satisfaction guaranteed|money back|free estimate|no obligation",  # guarantees
        r"license[d#]|bonded|insured|certified|accredited",  # service credentials
        r"new location|now open|grand opening|under new management",  # business announcements
        r"financing available|low monthly payments|no money down|credit terms",  # financing terms
    ]
    
    for pattern in ad_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Contains ad pattern: {pattern}"
    
    # News signals - expanded
    news_indicators = [
        # Common news byline patterns
        r"By [A-Z][a-z]+ [A-Z][a-z]+",
        r"[A-Z][a-z]+ [A-Z][a-z]+,? (?:Staff|Associated Press|Reuters|Special) (?:Writer|Reporter|Correspondent)",
        r"(?:Special|Staff) to [Tt]he (?:Express|News|Times|Post|Herald|Tribune|Gazette)",
        
        # Datelines - more comprehensive
        r"[A-Z]{2,}(?:,\s[A-Za-z\.]+\s+\d{1,2})?",
        r"[A-Z]+, [A-Za-z]+ \d{1,2} —",
        
        # News vocabulary
        r"(?:according to|reported|announced|officials|authorities|government|president|minister|spokesman)",
        r"(?:investigation|probe|inquiry|charged|ruling|resolution|legislation|regulation)",
        r"(?:bill|law|act|policy|court|judge|justice|case|ruling|decision|verdict)",
        
        # Attributions
        r"(?:said|stated|announced|confirmed|explained|testified|reported) (?:yesterday|today|last|this|on)",
        r"(?:noted|pointed out|emphasized|stressed|indicated|mentioned|commented)",
        
        # Event reporting
        r"(?:yesterday|last night|early today|earlier this|during the)",
        r"(?:press conference|statement|release|briefing|announcement|ceremony|interview)",
        
        # Political reporting
        r"(?:senate|congress|house|committee|administration|democrats?|republicans?|parliament|councilman|commissioner)",
        
        # Narrative structure
        r"(?:first|then|next|later|finally|eventually|subsequently)",
    ]
    
    # Count matches
    match_count = 0
    matches = []
    for pattern in news_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            match_count += 1
            matches.append(pattern)
    
    # Check for structural features
    has_news_structure = has_likely_news_structure(text)
    
    # News-specific paragraph patterns
    first_three_paras = text.split('\n\n')[:3]
    first_three_text = ' '.join(first_three_paras)
    
    # Look for quotes - strong indicator of news reporting
    quote_pattern = r'"([^"]{15,})"'
    has_quotes = bool(re.search(quote_pattern, text))
    
    # Check for 5W1H within first three paragraphs (who, what, when, where, why, how)
    five_w_one_h = r'\b(?:who|what|when|where|why|how)\b'
    has_five_w = len(re.findall(five_w_one_h, first_three_text, re.IGNORECASE)) >= 2
    
    # Paragraph structure analysis
    paragraphs = text.split('\n\n')
    if len(paragraphs) >= 4:
        # True news articles typically have multiple paragraphs with varied lengths
        para_lengths = [len(p) for p in paragraphs if p.strip()]
        if para_lengths:
            avg_para_len = sum(para_lengths) / len(para_lengths)
            # News paragraphs usually aren't extremely short or long
            has_good_para_structure = 20 <= avg_para_len <= 200
        else:
            has_good_para_structure = False
    else:
        has_good_para_structure = False
    
    # Scoring system - add up confidence indicators
    confidence_score = 0
    confidence_score += match_count  # Each matched pattern adds 1
    confidence_score += 2 if has_news_structure else 0
    confidence_score += 2 if has_quotes else 0
    confidence_score += 1 if has_five_w else 0
    confidence_score += 1 if has_good_para_structure else 0
    confidence_score += 2 if has_news_title else 0
    confidence_score += long_text_bonus
    
    # Very confident if high score
    if confidence_score >= 6:
        return True, f"High confidence: score {confidence_score}/10"
    
    # Somewhat confident
    if confidence_score >= 4:
        return True, f"Medium confidence: score {confidence_score}/10"
    
    # Check if first paragraph starts with location
    first_para = text.split('\n', 1)[0].strip() if '\n' in text else text[:100]
    location_start = re.match(r'^[A-Z]{2,}(?:,|\s*[-—])', first_para)
    
    if location_start and match_count >= 1:
        return True, "Starts with location and has news indicator"
    
    # Not enough evidence of being news
    return False, f"Insufficient news indicators: score {confidence_score}/10"

def process_articles(article_files, max_articles=None):
    """
    Process articles to identify likely news articles.
    
    Args:
        article_files (list): List of article file paths
        max_articles (int): Maximum number of news articles to identify
        
    Returns:
        tuple: (news_count, other_count, news_files, other_files)
    """
    news_count = 0
    other_count = 0
    news_files = []
    other_files = []
    
    for file_path in tqdm(article_files, desc="Finding news articles"):
        if max_articles and news_count >= max_articles:
            break
            
        # Load the article
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            continue
        
        # Check if it's likely news
        is_news, reason = is_likely_news(article_data)
        
        if is_news:
            news_count += 1
            news_files.append(file_path)
            
            # Save to news directory with metadata
            article_data["detected_news"] = True
            article_data["news_detection_reason"] = reason
            news_output_path = NEWS_DIR / file_path.name
            
            with open(news_output_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, indent=2)
        else:
            other_count += 1
            other_files.append(file_path)
    
    return news_count, other_count, news_files, other_files

def save_report(date_str, news_count, other_count, news_files):
    """
    Save a processing report with statistics.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        news_count (int): Number of detected news articles
        other_count (int): Number of other articles
        news_files (list): List of news article file paths
    """
    report = {
        "date": date_str,
        "total_articles": news_count + other_count,
        "news_articles": news_count,
        "other_articles": other_count,
        "news_percentage": round((news_count / (news_count + other_count)) * 100, 2) if (news_count + other_count) > 0 else 0,
        "news_files": [str(f) for f in news_files]
    }
    
    report_path = OUTPUT_DIR / f"news_prefilter_report_{date_str}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Report saved to {report_path}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Find high-confidence news articles')
    parser.add_argument('date', help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--max-articles', type=int, help='Maximum number of news articles to identify')
    args = parser.parse_args()
    
    date_str = args.date
    max_articles = args.max_articles
    
    ensure_directories()
    
    # Load and process articles
    article_files = load_articles(date_str)
    news_count, other_count, news_files, other_files = process_articles(article_files, max_articles)
    
    # Save the report
    save_report(date_str, news_count, other_count, news_files)
    
    # Print summary
    logger.info(f"Processed {news_count + other_count} articles")
    logger.info(f"Identified {news_count} news articles ({round((news_count / (news_count + other_count)) * 100, 2)}%)")
    logger.info(f"Excluded {other_count} non-news articles")
    
    # Create a file list for the classification step
    news_list_path = OUTPUT_DIR / f"high_confidence_news_{date_str}.txt"
    with open(news_list_path, 'w', encoding='utf-8') as f:
        for file_path in news_files:
            f.write(f"{file_path}\n")
    
    logger.info(f"News file list saved to {news_list_path}")
    logger.info(f"Next step: Run classify_articles.py with --file-list {news_list_path}")

if __name__ == "__main__":
    main() 