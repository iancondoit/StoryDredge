#!/usr/bin/env python3
"""
migrate_and_sanitize.py - Migrate classified articles to date-based directory structure and sanitize content

Usage:
    python migrate_and_sanitize.py [--date=<YYYY-MM-DD>]
    
Example:
    python migrate_and_sanitize.py
    python migrate_and_sanitize.py --date=1977-08-14
"""

import os
import sys
import json
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import shutil
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('migrate')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CLASSIFIED_DIR = OUTPUT_DIR / "classified"

# Constants
SOURCE_DIR = CLASSIFIED_DIR
TARGET_PROJECT_ROOT = CLASSIFIED_DIR

def ensure_directories(date_str=None):
    """Ensure necessary directories exist."""
    if date_str:
        (CLASSIFIED_DIR / date_str).mkdir(parents=True, exist_ok=True)
    else:
        CLASSIFIED_DIR.mkdir(parents=True, exist_ok=True)

def create_directory_structure(year, month, day):
    """Create the nested directory structure if it doesn't exist."""
    target_dir = os.path.join(TARGET_PROJECT_ROOT, year, month, day)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

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

def process_files():
    """Process JSON files, migrate them to the proper directory, and sanitize content."""
    stats = {
        "processed": 0,
        "skipped": 0,
        "examples": []
    }
    
    # List all JSON files in the source directory
    json_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.json')]
    total_files = len(json_files)
    
    print(f"Found {total_files} JSON files to process.")
    
    for filename in json_files:
        source_path = os.path.join(SOURCE_DIR, filename)
        
        try:
            # Read the JSON file
            with open(source_path, 'r', encoding='utf-8') as file:
                article_data = json.load(file)
            
            # Extract timestamp to get year, month, day
            timestamp = article_data.get('timestamp')
            if not timestamp:
                print(f"Warning: No timestamp found in {filename}. Skipping...")
                stats["skipped"] += 1
                continue
            
            # Parse the timestamp (expected format: YYYY-MM-DD)
            date_parts = timestamp.split('-')
            if len(date_parts) != 3:
                print(f"Warning: Invalid timestamp format in {filename}: {timestamp}. Skipping...")
                stats["skipped"] += 1
                continue
            
            year, month, day = date_parts
            
            # Create target directory
            target_dir = create_directory_structure(year, month, day)
            target_path = os.path.join(target_dir, filename)
            
            # Store original body for example
            original_body = article_data.get('body', '')
            
            # Sanitize body content
            if 'body' in article_data and article_data['body']:
                article_data['body'] = sanitize_body_text(article_data['body'])
            
            # Write updated JSON to target location
            with open(target_path, 'w', encoding='utf-8') as file:
                json.dump(article_data, file, indent=2, ensure_ascii=False)
            
            stats["processed"] += 1
            
            # Store a few examples for the report
            if len(stats["examples"]) < 3 and original_body != article_data.get('body', ''):
                stats["examples"].append({
                    "filename": filename,
                    "before": original_body,
                    "after": article_data.get('body', '')
                })
            
            print(f"Processed: {filename} -> {target_path}")
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            stats["skipped"] += 1
    
    return stats

def print_report(stats):
    """Print a final report of the migration and sanitization process."""
    print("\n====== MIGRATION AND SANITIZATION REPORT ======")
    print(f"Total files processed: {stats['processed']}")
    print(f"Total files skipped: {stats['skipped']}")
    
    print("\n----- CLEANING EXAMPLES -----")
    for i, example in enumerate(stats["examples"], 1):
        print(f"\nEXAMPLE {i}: {example['filename']}")
        print("BEFORE:")
        print(f"{example['before']}")
        print("\nAFTER:")
        print(f"{example['after']}")
        print("-" * 50)
    
    print("\nMigration and sanitization complete!")

if __name__ == "__main__":
    # Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' does not exist.")
        exit(1)
        
    print(f"Starting migration and sanitization of articles from '{SOURCE_DIR}'...")
    stats = process_files()
    print_report(stats) 