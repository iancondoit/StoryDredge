import os
import json
import re
import glob
from collections import Counter

# Constants
CLASSIFIED_DIR = "output/classified"
HSA_READY_DIR = "output/hsa-ready"
REJECTED_DIR = "output/rejected"

# Filtering thresholds
MIN_BODY_LENGTH = 150
MIN_SENTENCES = 2
MAX_SYMBOL_RATIO = 0.25

# Additional ad-specific keywords and patterns
AD_KEYWORDS = [
    "sale", "discount", "special", "offer", "price", "buy", "call", "contact",
    "financing", "money", "cash", "credit", "cheap", "affordable", "deal",
    "service", "appointment", "opening", "rent", "lease", "property", "realty",
    "bedroom", "bath", "sq ft", "house", "home", "apartment", "condo", "office",
    "shop", "store", "mall", "phone", "wanted", "hiring", "position", "job",
    "employment", "salary", "wage", "benefit", "insurance", "opportunity", "resume",
    "interview", "apply", "application", "opening", "free", "low price", "clearance",
    "retail", "wholesale", "dealer", "dealership", "market"
]

# Compile the keywords into a case-insensitive regex pattern
AD_PATTERN = re.compile(r'(?i)\b(' + '|'.join(re.escape(kw) for kw in AD_KEYWORDS) + r')\b')

# Patterns for phone numbers, prices, etc.
PHONE_PATTERN = re.compile(r'(?<!\w)(\d{3}[-.)/ ]?\d{3}[-.)/ ]?\d{4})(?!\w)')
PRICE_PATTERN = re.compile(r'(?<!\w)\$\s*\d+(?:,\d{3})*(?:\.\d{2})?(?!\w)')
PERCENTAGE_PATTERN = re.compile(r'(?<!\w)\d+\s*%(?!\w)')
LOCATION_WITH_NUMBER_PATTERN = re.compile(r'\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+){1,3}(?:\s+[Rr]oad|[Ss]t|[Ss]treet|[Aa]ve|[Aa]venue|[Bb]lvd|[Bb]oulevard|[Ll]n|[Ll]ane|[Dd]r|[Dd]rive|[Cc]t|[Cc]ourt|[Pp]l|[Pp]lace)')

def sanitize_body_text(body):
    """Clean up the article body text."""
    if not body:
        return body
    
    # Remove excessive line breaks
    body = re.sub(r'\n{3,}', '\n\n', body)
    
    # Remove non-printable or weird characters
    body = re.sub(r'[*#©•\x00]', '', body)
    
    # Normalize punctuation spacing
    body = re.sub(r'\s+([,.!?:;])', r'\1', body)  # Remove space before punctuation
    body = re.sub(r'([,.!?:;])(\s*)\1+', r'\1', body)  # Remove duplicated punctuation
    body = re.sub(r'\.{2,}', '...', body)  # Normalize multiple periods to ellipsis
    
    # Fix broken spacing
    body = re.sub(r'\s{2,}', ' ', body)  # Multiple spaces to single space
    
    # Un-hyphenate words split across lines (optional)
    body = re.sub(r'(\w+)-\n(\w+)', r'\1\2', body)
    
    # Trim trailing and leading whitespace
    body = body.strip()
    
    return body

def count_sentences(text):
    """Count the number of sentences in a text (basic implementation)."""
    if not text:
        return 0
    
    # Simple heuristic: count sentence-ending punctuation
    sentence_endings = re.findall(r'[.!?]+', text)
    return len(sentence_endings)

def calculate_symbol_ratio(text):
    """Calculate the ratio of symbols to words in a text."""
    if not text:
        return 1.0  # Maximum ratio for empty text
    
    # Count words (sequences of alphanumeric characters)
    words = re.findall(r'\w+', text)
    # Count symbols (non-alphanumeric, non-whitespace characters)
    symbols = re.findall(r'[^\w\s]', text)
    
    if not words:
        return 1.0  # Maximum ratio if no words
    
    return len(symbols) / len(words)

def is_likely_ad(article):
    """Check if article is likely an advertisement using stricter criteria."""
    # Get article fields
    headline = article.get("headline", "")
    body = article.get("body", "")
    byline = article.get("byline", "")
    section = article.get("section", "").lower()
    tags = article.get("tags", [])
    
    # Check tags for ad-related words
    for tag in tags:
        if any(ad_word in tag.lower() for ad_word in ["ad", "advertisement", "classified", "listing", "shopping"]):
            return True, "Ad-related tag found"
    
    combined_text = f"{headline} {body} {byline}".lower()
    
    # Check for a high concentration of AD_KEYWORDS (more than 3 unique ones)
    ad_matches = set(re.findall(AD_PATTERN, combined_text))
    if len(ad_matches) >= 3:
        return True, f"Multiple ad keywords found"
    
    # Check for phone numbers (more than 1)
    phone_matches = re.findall(PHONE_PATTERN, combined_text)
    if len(phone_matches) > 1:
        return True, "Multiple phone numbers"
    
    # Check for prices (more than 1)
    price_matches = re.findall(PRICE_PATTERN, combined_text)
    if len(price_matches) > 1:
        return True, "Multiple price mentions"
    
    # Check for percentages (discounts)
    percentage_matches = re.findall(PERCENTAGE_PATTERN, combined_text)
    if len(percentage_matches) > 1:
        return True, "Multiple percentage mentions (likely discounts)"
    
    # Check for business addresses
    location_matches = re.findall(LOCATION_WITH_NUMBER_PATTERN, combined_text)
    if location_matches:
        return True, "Contains business address"
    
    # Check for common ad phrases and calls to action
    ad_phrases = [
        "call now", "call today", "for appointment", "free estimate",
        "open house", "open sunday", "call for", "for information",
        "for details", "buy now", "limited time", "apply today",
        "walk-in", "come see", "sale ends", "don't miss", "visit us"
    ]
    for phrase in ad_phrases:
        if phrase in combined_text:
            return True, f"Contains ad phrase"
    
    # Check for short paragraphs with bullets or lists (common in ads)
    lines = body.split('\n')
    bullet_count = sum(1 for line in lines if line.strip().startswith(('•', '-', '*', '–')))
    if bullet_count >= 3:
        return True, "Contains multiple bullet points (likely a list or ad)"
    
    # Check for real estate listings
    real_estate_indicators = [
        "bedroom", "bath", "sq ft", "square foot", "lot size",
        "acreage", "open floor plan", "master suite", "garage"
    ]
    re_matches = [indicator for indicator in real_estate_indicators if indicator in combined_text]
    if len(re_matches) >= 2:
        return True, "Contains multiple real estate listing indicators"
    
    # Check for event listings with times and dates
    event_indicators = [
        "admission", "tickets", "event", "show", "performance", "concert",
        "exhibit", "exhibition", "gallery", "matinee", "pm", "am"
    ]
    date_pattern = r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}\b'
    time_pattern = r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b'
    
    event_matches = [indicator for indicator in event_indicators if indicator in combined_text.lower()]
    has_date = re.search(date_pattern, combined_text.lower())
    has_time = re.search(time_pattern, combined_text.lower())
    
    if len(event_matches) >= 2 and (has_date or has_time):
        return True, "Appears to be an event listing"
    
    # Not detected as an ad
    return False, None

def should_exclude_article(article):
    """Determine if an article should be excluded based on filtering rules."""
    # Check section type
    section = article.get("section", "").lower()
    if section in ["ad", "classified", "unknown"]:
        return True, "Section type excluded"
    
    # Check if headline or body is missing
    if not article.get("headline"):
        return True, "Missing headline"
    
    body = article.get("body", "")
    if not body:
        return True, "Missing body"
    
    # Check body length
    if len(body) < MIN_BODY_LENGTH:
        return True, "Body too short"
    
    # Check sentence count
    if count_sentences(body) < MIN_SENTENCES:
        return True, "Too few sentences"
    
    # Check symbol ratio
    if calculate_symbol_ratio(body) > MAX_SYMBOL_RATIO:
        return True, "High symbol-to-word ratio"
    
    # Check if it's likely an ad
    is_ad, reason = is_likely_ad(article)
    if is_ad:
        return True, reason
    
    # If we reached here, the article passes all filters
    return False, None

def create_directory(path):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def process_issue(year, month, day):
    """
    Process a single issue, filtering out non-news content.
    
    Args:
        year (str): Year (YYYY)
        month (str): Month (MM)
        day (str): Day (DD)
        
    Returns:
        dict: Results of processing
    """
    # Set up paths
    issue_dir = os.path.join(CLASSIFIED_DIR, year, month, day)
    hsa_ready_dir = os.path.join(HSA_READY_DIR, year, month, day)
    rejected_dir = os.path.join(REJECTED_DIR, year, month, day)
    
    # Create output directories
    create_directory(hsa_ready_dir)
    create_directory(rejected_dir)
    
    # Find all JSON files in the issue directory
    files = glob.glob(os.path.join(issue_dir, "*.json"))
    
    # Set up results counter
    results = {
        "total": len(files),
        "usable": 0,
        "rejected": 0,
        "rejection_reasons": Counter()
    }
    
    # Process each file
    for file_path in files:
        filename = os.path.basename(file_path)
        
        try:
            # Read the article JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                article = json.load(f)
            
            # Check if the article should be excluded
            exclude, reason = should_exclude_article(article)
            
            if exclude:
                # Mark the article as skipped and add reason
                article["skip_hsa"] = True
                article["skip_hsa_reason"] = reason if reason else "Low content quality or non-narrative content"
                
                # Save to rejected folder
                rejected_path = os.path.join(rejected_dir, filename)
                with open(rejected_path, 'w', encoding='utf-8') as f:
                    json.dump(article, f, indent=2, ensure_ascii=False)
                
                results["rejected"] += 1
                results["rejection_reasons"][reason] += 1
            else:
                # Ensure the body is clean
                article["body"] = sanitize_body_text(article.get("body", ""))
                
                # Save to HSA-ready folder
                hsa_ready_path = os.path.join(hsa_ready_dir, filename)
                with open(hsa_ready_path, 'w', encoding='utf-8') as f:
                    json.dump(article, f, indent=2, ensure_ascii=False)
                
                results["usable"] += 1
        
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            results["rejected"] += 1
            results["rejection_reasons"]["Processing error"] += 1
    
    return results

def update_issue_index(year, month, day, results):
    """Update the issue's index.json with statistics."""
    index_dir = os.path.join("output")
    index_path = os.path.join(index_dir, "index.json")
    
    # Create or load existing index
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {}
    
    # Create or update issue entry
    issue_id = f"{year}-{month}-{day}"
    if issue_id not in index:
        index[issue_id] = {}
    
    # Update statistics
    index[issue_id]["hsa_ready_count"] = results["usable"]
    index[issue_id]["rejected_count"] = results["rejected"]
    
    # Save updated index
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def print_report(results):
    """Print a report of processing results."""
    print("\n====== HSA FILTERING REPORT ======")
    print(f"Total articles: {results['total']}")
    print(f"Usable for HSA: {results['usable']}")
    print(f"Rejected: {results['rejected']}")
    
    if results["rejection_reasons"]:
        print("\nRejection reasons:")
        for reason, count in results["rejection_reasons"].most_common():
            print(f"  - {reason}: {count}")
    
    print("\nHSA filtering complete!")

def process_all_issues():
    """Process all issues in the classified directory."""
    grand_total = {"total": 0, "usable": 0, "rejected": 0, "rejection_reasons": Counter()}
    
    # Find all year directories
    year_dirs = [d for d in os.listdir(CLASSIFIED_DIR) if os.path.isdir(os.path.join(CLASSIFIED_DIR, d))]
    
    for year in year_dirs:
        month_dirs = [d for d in os.listdir(os.path.join(CLASSIFIED_DIR, year)) 
                     if os.path.isdir(os.path.join(CLASSIFIED_DIR, year, d))]
        
        for month in month_dirs:
            day_dirs = [d for d in os.listdir(os.path.join(CLASSIFIED_DIR, year, month)) 
                       if os.path.isdir(os.path.join(CLASSIFIED_DIR, year, month, d))]
            
            for day in day_dirs:
                print(f"Processing issue: {year}-{month}-{day}")
                results = process_issue(year, month, day)
                
                # Update global stats
                grand_total["total"] += results["total"]
                grand_total["usable"] += results["usable"]
                grand_total["rejected"] += results["rejected"]
                
                for reason, count in results["rejection_reasons"].items():
                    grand_total["rejection_reasons"][reason] += count
                
                # Update issue index
                update_issue_index(year, month, day, results)
    
    return grand_total

if __name__ == "__main__":
    print("Starting HSA filtering process...")
    
    # Create output directories if they don't exist
    create_directory(HSA_READY_DIR)
    create_directory(REJECTED_DIR)
    
    # Process all classified articles
    results = process_all_issues()
    
    # Print final report
    print_report(results) 