#!/usr/bin/env python3
"""
clean_text.py - Cleans and normalizes raw OCR text

Usage:
    python clean_text.py <date>
    
Example:
    python clean_text.py 1977-08-14
"""

import re
import sys
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('clean_text')

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "archive"
RAW_DIR = ARCHIVE_DIR / "raw"
CLEANED_DIR = ARCHIVE_DIR / "cleaned"  # Changed from PROCESSED_DIR to match expected path
DATA_DIR = PROJECT_ROOT / "data"
INDEX_FILE = DATA_DIR / "index.json"

def ensure_directories():
    """Ensure necessary directories exist."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_raw_text(date_str):
    """
    Load raw OCR text from file.
    
    Args:
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        str: Raw OCR text content
    """
    input_file = RAW_DIR / f"{date_str}.txt"
    
    if not input_file.exists():
        logger.error(f"Error: Raw OCR file not found: {input_file}")
        sys.exit(1)
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading raw text file {input_file}: {str(e)}")
        # Return empty string instead of exiting so we can handle the error gracefully
        return ""

def update_index(date_str, clean_file):
    """Update the index.json file with information about the processed issue."""
    try:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r') as f:
                index_data = json.load(f)
        else:
            logger.warning("Index file not found. Creating new index.")
            index_data = {"processed_issues": []}
        
        # Find the issue by date
        found = False
        for issue in index_data.get("processed_issues", []):
            if issue.get("date") == date_str:
                issue["status"] = "cleaned"
                issue["clean_file"] = str(clean_file)
                found = True
                break
        
        # If issue not found, add it
        if not found:
            index_data.setdefault("processed_issues", []).append({
                "date": date_str,
                "status": "cleaned",
                "clean_file": str(clean_file)
            })
        
        # Save updated index
        with open(INDEX_FILE, 'w') as f:
            json.dump(index_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error updating index file: {str(e)}")
        # Continue processing even if index update fails

def clean_text(text):
    """
    Clean and normalize OCR text.
    
    Args:
        text (str): Raw OCR text
        
    Returns:
        str: Cleaned text
    """
    # Check for empty text
    if not text or len(text.strip()) == 0:
        logger.warning("Empty or whitespace-only text provided for cleaning")
        return ""
    
    try:
        # Remove page headers/footers and page numbers (typically contains page numbers)
        # Look for patterns like "Page 4" or "4 San Antonio Express"
        text = re.sub(r'(?m)^.*?Page\s+\d+.*?$', '', text)
        text = re.sub(r'(?m)^\d+\s+.*?(?:Express|News|Times|Tribune).*?$', '', text)
        
        # Remove line breaks inside paragraphs (but preserve paragraph breaks)
        # First, normalize all line endings
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # Handle hyphenated words at end of lines
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # Join lines that don't end with punctuation (preserving paragraph structure)
        text = re.sub(r'([^.!?:])\n([a-z])', r'\1 \2', text)
        
        # Remove excess whitespace
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple line breaks to double line break
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Fix common OCR errors
        text = text.replace('l1', 'h').replace('0', 'o')  # Example replacements
        
        # Trim leading and trailing whitespace
        text = text.strip()
        
        return text
    except Exception as e:
        logger.error(f"Error during text cleaning: {str(e)}")
        # Return original text if cleaning fails
        return text

def main():
    """Main function."""
    try:
        ensure_directories()
        
        if len(sys.argv) < 2:
            logger.error("Usage: python clean_text.py <date>")
            logger.error("Example: python clean_text.py 1977-08-14")
            return 1
        
        date_str = sys.argv[1]
        
        # Load raw text
        logger.info(f"Loading raw OCR text for date: {date_str}")
        raw_text = load_raw_text(date_str)
        
        if not raw_text:
            logger.error(f"No valid text content found for {date_str}")
            return 1
        
        # Clean the text
        logger.info("Cleaning and normalizing text...")
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text:
            logger.error("Cleaning resulted in empty text. Check the raw text file.")
            return 1
        
        # Save the cleaned text - using the correct output directory and filename
        output_file = CLEANED_DIR / f"{date_str}.txt"  # Changed filename format
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        # Update index
        update_index(date_str, output_file)
        
        logger.info(f"Successfully cleaned text and saved to: {output_file}")
        logger.info(f"Original text size: {len(raw_text)} characters")
        logger.info(f"Cleaned text size: {len(cleaned_text)} characters")
        if len(raw_text) > 0:
            logger.info(f"Reduction: {(1 - len(cleaned_text)/len(raw_text))*100:.2f}%")
        
        return 0
    except Exception as e:
        logger.error(f"Unexpected error in clean_text.py: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 