#!/usr/bin/env python3
"""
fetch_issue.py - Downloads and extracts OCR text from archive.org

Usage:
    python fetch_issue.py <archive_id>
    
Example:
    python fetch_issue.py san-antonio-express-news-1977-08-14
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "archive" / "raw"
DATA_DIR = BASE_DIR / "data"
INDEX_FILE = DATA_DIR / "index.json"

def ensure_directories():
    """Ensure necessary directories exist."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_ocr_text(archive_id):
    """
    Download the djvu.txt OCR file from archive.org for the given archive_id.
    
    Args:
        archive_id (str): The archive.org identifier
        
    Returns:
        Path: Path to the downloaded file or None if failed
    """
    # Extract date from archive_id (assuming format: publication-YYYY-MM-DD)
    parts = archive_id.split('-')
    try:
        # Extract date parts
        year = parts[-3]
        month = parts[-2]
        day = parts[-1]
        date_str = f"{year}-{month}-{day}"
    except IndexError:
        date_str = datetime.now().strftime("%Y-%m-%d")
        print(f"Warning: Could not extract date from archive_id, using today's date: {date_str}")
    
    # Construct download URL
    download_url = f"https://archive.org/download/{archive_id}/{archive_id}_djvu.txt"
    
    print(f"Downloading OCR text from: {download_url}")
    
    # Download the file
    response = requests.get(download_url, stream=True)
    
    if response.status_code != 200:
        print(f"Error: Could not download file (Status code: {response.status_code})")
        return None
    
    # Save the file
    output_file = RAW_DIR / f"{date_str}.txt"
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    
    with open(output_file, 'wb') as f:
        with tqdm(total=total_size, unit='iB', unit_scale=True, desc="Downloading") as pbar:
            for data in response.iter_content(block_size):
                f.write(data)
                pbar.update(len(data))
    
    # Update index file
    update_index(archive_id, date_str, output_file)
    
    print(f"Successfully downloaded OCR text to: {output_file}")
    return output_file

def update_index(archive_id, date_str, output_file):
    """Update the index.json file with information about the downloaded issue."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r') as f:
            index_data = json.load(f)
    else:
        index_data = {"processed_issues": []}
    
    # Check if archive_id already exists
    for issue in index_data["processed_issues"]:
        if issue["id"] == archive_id:
            issue["status"] = "downloaded"
            break
    else:
        # Add new entry
        publication = os.getenv("DEFAULT_PUBLICATION", "Unknown")
        new_issue = {
            "id": archive_id,
            "date": date_str,
            "publication": publication,
            "url": f"https://archive.org/details/{archive_id}",
            "status": "downloaded",
            "article_count": 0,
            "raw_file": str(output_file)
        }
        index_data["processed_issues"].append(new_issue)
    
    # Save updated index
    with open(INDEX_FILE, 'w') as f:
        json.dump(index_data, f, indent=2)

def main():
    """Main function."""
    ensure_directories()
    
    if len(sys.argv) < 2:
        print("Usage: python fetch_issue.py <archive_id>")
        print("Example: python fetch_issue.py san-antonio-express-news-1977-08-14")
        return
    
    archive_id = sys.argv[1]
    download_ocr_text(archive_id)

if __name__ == "__main__":
    main() 