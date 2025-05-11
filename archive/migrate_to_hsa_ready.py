#!/usr/bin/env python3
"""
migrate_to_hsa_ready.py - Move processed articles to the hsa-ready directory structure
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

def migrate_articles():
    """Migrate processed articles to hsa-ready structure"""
    
    workspace_dir = Path().resolve()
    output_dir = workspace_dir / "output"
    classified_dir = output_dir / "classified"
    hsa_ready_dir = output_dir / "hsa-ready"
    
    # Ensure hsa-ready directory exists
    hsa_ready_dir.mkdir(exist_ok=True, parents=True)
    
    # Get list of dates from date file
    date_file = workspace_dir / "sa_dates.txt"
    processed_dates = []
    
    if date_file.exists():
        with open(date_file, 'r') as f:
            processed_dates = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(processed_dates)} dates to migrate")
    
    # Process each date
    for date_str in processed_dates:
        try:
            year, month, day = date_str.split('-')
            
            # Source directory with classified articles
            source_dir = classified_dir / date_str
            
            if not source_dir.exists():
                print(f"No classified articles found for {date_str}, skipping")
                continue
                
            # Destination directory in hsa-ready format
            dest_dir = hsa_ready_dir / year / month / day
            dest_dir.mkdir(exist_ok=True, parents=True)
            
            # Get all JSON files in the source directory
            json_files = list(source_dir.glob("*.json"))
            article_files = [f for f in json_files if f.name != f"report-{date_str}.json"]
            
            print(f"Processing {date_str}: {len(article_files)} articles")
            
            # Process each article file
            for article_file in article_files:
                try:
                    with open(article_file, 'r') as f:
                        article = json.load(f)
                    
                    # Create standardized filename
                    filename = f"{date_str}--{article_file.stem.split('--')[-1]}.json"
                    dest_file = dest_dir / filename
                    
                    # Copy file to destination
                    shutil.copy2(article_file, dest_file)
                    
                except Exception as e:
                    print(f"Error processing article {article_file}: {e}")
            
            print(f"Successfully migrated articles for {date_str}")
            
        except Exception as e:
            print(f"Error processing date {date_str}: {e}")
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate_articles()
