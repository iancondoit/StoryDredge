#!/usr/bin/env python3
"""
cleanup_hsa_ready.py - Aggressively filter ad and classified content from the HSA-ready directory
"""

import os
import json
import re
import shutil
from pathlib import Path
import argparse
from collections import Counter

# Directories
HSA_READY_DIR = "output/hsa-ready"
REJECTED_DIR = "output/rejected"

# Additional ad-specific keywords and patterns beyond what's in the filter_and_finalize.py
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

def is_likely_ad(article):
    """Check if article is likely an advertisement using stricter criteria."""
    # Get article fields
    headline = article.get("headline", "")
    body = article.get("body", "")
    byline = article.get("byline", "")
    section = article.get("section", "").lower()
    tags = article.get("tags", [])
    
    # Immediate exclusions based on section
    if section in ["ad", "classified"]:
        return True, "Explicitly marked as ad/classified"
    
    # Check tags for ad-related words
    for tag in tags:
        if any(ad_word in tag.lower() for ad_word in ["ad", "advertisement", "classified", "listing", "shopping"]):
            return True, "Ad-related tag found"
    
    combined_text = f"{headline} {body} {byline}".lower()
    
    # Check for a high concentration of AD_KEYWORDS (more than 3 unique ones)
    ad_matches = set(re.findall(AD_PATTERN, combined_text))
    if len(ad_matches) >= 3:
        return True, f"Multiple ad keywords: {', '.join(list(ad_matches)[:5])}"
    
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
            return True, f"Contains ad phrase: '{phrase}'"
    
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

def process_hsa_ready():
    """Process all files in the HSA-ready directory to remove ads."""
    # Create directories
    os.makedirs(REJECTED_DIR, exist_ok=True)
    
    # Statistics for report
    total_files = 0
    removed_files = 0
    reasons = Counter()
    
    # Recursively find and process all JSON files
    for root, _, files in os.walk(HSA_READY_DIR):
        for filename in files:
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(root, filename)
            total_files += 1
            
            # Load the article
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                
                # Check if it's likely an ad
                is_ad, reason = is_likely_ad(article)
                
                if is_ad:
                    # Get the issue date and construct directory structure in rejected directory
                    timestamp = article.get("timestamp", "unknown")
                    
                    # Create rejection directory structure
                    if timestamp != "unknown" and len(timestamp.split("-")) == 3:
                        year, month, day = timestamp.split("-")
                        target_dir = os.path.join(REJECTED_DIR, "cleaned", year, month, day)
                    else:
                        target_dir = os.path.join(REJECTED_DIR, "cleaned", "unknown")
                    
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Move the file to rejected directory
                    target_path = os.path.join(target_dir, filename)
                    
                    # Add rejection reason
                    article["skip_hsa"] = True
                    article["skip_hsa_reason"] = reason
                    
                    # Save to rejected folder
                    with open(target_path, 'w', encoding='utf-8') as f:
                        json.dump(article, f, indent=2, ensure_ascii=False)
                    
                    # Delete from HSA-ready folder
                    os.remove(file_path)
                    
                    removed_files += 1
                    reasons[reason] += 1
                    
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
    
    return total_files, removed_files, reasons

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Clean up HSA-ready directory by removing ad/classified content')
    args = parser.parse_args()
    
    print("Starting aggressive cleanup of HSA-ready directory...")
    total_files, removed_files, reasons = process_hsa_ready()
    
    # Print report
    print("\n====== CLEANUP REPORT ======")
    print(f"Total files scanned: {total_files}")
    print(f"Ads/classifieds removed: {removed_files}")
    
    if reasons:
        print("\nRemoval reasons:")
        for reason, count in reasons.most_common():
            print(f"  - {reason}: {count}")
    
    print(f"\nCleanup complete! Removed {removed_files} items from HSA-ready directory.")

if __name__ == "__main__":
    main() 