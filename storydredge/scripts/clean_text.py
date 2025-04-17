#!/usr/bin/env python3
"""
clean_text.py - Cleans and normalizes OCR text from newspaper issues

Usage:
    python clean_text.py <date>
    
Example:
    python clean_text.py 1977-08-14
"""

import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "archive" / "raw"
PROCESSED_DIR = BASE_DIR / "archive" / "processed"
DATA_DIR = BASE_DIR / "data"
INDEX_FILE = DATA_DIR / "index.json"

def ensure_directories():
    """Ensure necessary directories exist."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

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
        print(f"Error: Raw OCR file not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def update_index(date_str, clean_file):
    """Update the index.json file with information about the processed issue."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index_data = json.load(f)
    else:
        print("Error: Index file not found. Run fetch_issue.py first.")
        return
    
    # Find the issue by date
    for issue in index_data.get("processed_issues", []):
        if issue.get("date") == date_str:
            issue["status"] = "cleaned"
            issue["clean_file"] = str(clean_file)
            break
    
    # Save updated index
    with open(INDEX_FILE, 'w') as f:
        json.dump(index_data, f, indent=2)

def clean_text(text):
    """
    Clean and normalize OCR text.
    
    Args:
        text (str): Raw OCR text
        
    Returns:
        str: Cleaned text
    """
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

def main():
    """Main function."""
    ensure_directories()
    
    if len(sys.argv) < 2:
        print("Usage: python clean_text.py <date>")
        print("Example: python clean_text.py 1977-08-14")
        return
    
    date_str = sys.argv[1]
    
    # Load raw text
    print(f"Loading raw OCR text for date: {date_str}")
    raw_text = load_raw_text(date_str)
    
    # Clean the text
    print("Cleaning and normalizing text...")
    cleaned_text = clean_text(raw_text)
    
    # Save the cleaned text
    output_file = PROCESSED_DIR / f"{date_str}-clean.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)
    
    # Update index
    update_index(date_str, output_file)
    
    print(f"Successfully cleaned text and saved to: {output_file}")
    print(f"Original text size: {len(raw_text)} characters")
    print(f"Cleaned text size: {len(cleaned_text)} characters")
    print(f"Reduction: {(1 - len(cleaned_text)/len(raw_text))*100:.2f}%")

if __name__ == "__main__":
    main() 