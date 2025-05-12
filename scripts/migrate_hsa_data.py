#!/usr/bin/env python3
"""
HSA-Ready Data Migration Script

This script reorganizes the HSA-ready data into a clean structure organized by:
- Publication
- Year
- Month
- Day

It also fixes any issues with file formatting, removes hidden files,
and ensures all files follow a consistent naming convention.

Modified to work with articles extracted by test_atlanta_constitution_direct.py
which contain only 'title' and 'raw_text' fields.
"""

import os
import json
import sys
import shutil
import re
from pathlib import Path
from datetime import datetime
import logging
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hsa_migrator")

# Required fields for HSA files
REQUIRED_FIELDS = [
    "headline", 
    "body", 
    "section", 
    "timestamp", 
    "publication",
    "source_issue",
    "source_url"
]

class HSAMigrator:
    """Migrates HSA-ready data to a clean structure."""

    def __init__(self, source_dir="output", target_dir="output/hsa-ready"):
        """Initialize with source and target directories."""
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.stats = {
            "total_files": 0,
            "migrated_files": 0,
            "skipped_files": 0,
            "fixed_files": 0,
            "by_publication": {},
            "by_year": {}
        }
        
    def clean_publication_name(self, publication):
        """Convert publication name to a clean format for directory names."""
        # Replace spaces with underscores and remove special characters
        clean_name = re.sub(r'[^\w\s-]', '', publication)
        clean_name = re.sub(r'\s+', '_', clean_name)
        return clean_name.lower().strip()
        
    def migrate(self):
        """Perform the migration of HSA-ready files."""
        logger.info(f"Starting migration from {self.source_dir} to {self.target_dir}")
        
        if not self.source_dir.exists():
            logger.error(f"Source directory {self.source_dir} does not exist")
            return False
            
        # Create target directory if it doesn't exist
        self.target_dir.mkdir(parents=True, exist_ok=True)
            
        # Walk through all files in output directory
        for root, dirs, files in os.walk(self.source_dir):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                # Skip hidden and non-JSON files
                if file.startswith('.') or not file.endswith('.json'):
                    continue
                
                # Make sure we're only processing article files in an articles directory
                if not "articles" in root:
                    continue
                    
                file_path = Path(root) / file
                self.migrate_file(file_path)
                
        logger.info(f"Migration complete. Migrated {self.stats['migrated_files']} of {self.stats['total_files']} files.")
        return True
        
    def extract_info_from_path(self, file_path):
        """Extract publication and date info from issue path."""
        # Extract issue ID from path
        # Example: output/per_atlanta-constitution_1922-01-01_54_203/articles/article_0001.json
        parts = file_path.parts
        issue_id = None
        
        # Find the part that contains the issue ID
        for part in parts:
            if part.startswith("per_"):
                issue_id = part
                break
        
        if not issue_id:
            return None, None, None, None, None
        
        # Extract publication and date from issue ID
        # Example: per_atlanta-constitution_1922-01-01_54_203
        parts = issue_id.split("_")
        if len(parts) < 3:
            return None, None, None, None, None
        
        publication = parts[1]
        date_str = parts[2]
        
        # Extract year, month, day from date
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if not match:
            return publication, None, None, None, issue_id
        
        year, month, day = match.groups()
        return publication, year, month, day, issue_id
        
    def migrate_file(self, file_path):
        """Migrate a single article file."""
        self.stats["total_files"] += 1
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract publication and date info from file path
            publication, year, month, day, issue_id = self.extract_info_from_path(file_path)
            
            if not publication or not year or not month or not day:
                logger.warning(f"Skipping file {file_path}: Could not extract publication or date info")
                self.stats["skipped_files"] += 1
                return
            
            # Convert to HSA format
            hsa_article = self.convert_to_hsa_format(data, publication, year, month, day, issue_id)
            
            # Keep track of publications
            clean_publication = self.clean_publication_name(publication)
            if clean_publication not in self.stats["by_publication"]:
                self.stats["by_publication"][clean_publication] = 0
            self.stats["by_publication"][clean_publication] += 1
            
            # Keep track of years
            if year not in self.stats["by_year"]:
                self.stats["by_year"][year] = 0
            self.stats["by_year"][year] += 1
            
            # Create target directory structure
            target_dir = self.target_dir / clean_publication / year / month / day
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a clean filename using headline or a portion of it
            if "headline" in hsa_article and hsa_article["headline"]:
                # Clean headline for filename
                clean_headline = re.sub(r'[^\w\s-]', '', hsa_article["headline"])
                clean_headline = re.sub(r'\s+', '-', clean_headline)
                clean_headline = clean_headline.lower()[:50]  # Limit length
                filename = f"{year}-{month}-{day}--{clean_headline}.json"
            else:
                # Use a generic name with ID
                article_id = str(uuid.uuid4())
                filename = f"{year}-{month}-{day}--article-{article_id}.json"
            
            # Full target path
            target_path = target_dir / filename
            
            # Write the updated file
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(hsa_article, f, indent=2)
                
            self.stats["migrated_files"] += 1
            logger.info(f"Migrated: {file_path.name} -> {target_path}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON in file {file_path}")
            self.stats["skipped_files"] += 1
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            self.stats["skipped_files"] += 1
    
    def convert_to_hsa_format(self, article, publication, year, month, day, issue_id):
        """Convert article extracted by direct_test to HSA format."""
        hsa_article = {}
        
        # Copy title to headline
        hsa_article["headline"] = article.get("title", "Untitled")
        
        # Copy raw_text to body
        hsa_article["body"] = article.get("raw_text", "")
        
        # Add required fields
        hsa_article["section"] = "news"  # Default section
        hsa_article["tags"] = []  # Empty tags array
        
        # Format timestamp
        timestamp = f"{year}-{month}-{day}T00:00:00.000Z"
        hsa_article["timestamp"] = timestamp
        
        # Set publication info
        hsa_article["publication"] = f"The Atlanta Constitution"
        hsa_article["source_issue"] = issue_id
        hsa_article["source_url"] = f"https://archive.org/details/{issue_id}"
        
        return hsa_article
            
    def extract_date_parts(self, timestamp):
        """Extract year, month, day from a timestamp."""
        try:
            # Handle different timestamp formats
            if "T" in timestamp:
                date_part = timestamp.split("T")[0]
            else:
                date_part = timestamp
                
            # Extract year, month, day
            parts = date_part.split("-")
            if len(parts) >= 3:
                return parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                return parts[0], parts[1], "01"  # Default to 1st of month
            else:
                return parts[0], "01", "01"  # Default to Jan 1
        except Exception:
            # Default to current date if can't parse
            now = datetime.now()
            return str(now.year), str(now.month).zfill(2), str(now.day).zfill(2)
            
    def generate_report(self, output_file=None):
        """Generate a report of the migration results."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_directory": str(self.source_dir),
            "target_directory": str(self.target_dir),
            "summary": {
                "total_files": self.stats["total_files"],
                "migrated_files": self.stats["migrated_files"],
                "skipped_files": self.stats["skipped_files"],
                "fixed_files": self.stats["fixed_files"],
                "success_rate": (self.stats["migrated_files"] / self.stats["total_files"] * 100) if self.stats["total_files"] > 0 else 0
            },
            "by_publication": self.stats["by_publication"],
            "by_year": self.stats["by_year"]
        }
        
        # Print summary to console
        logger.info(f"Migration Summary:")
        logger.info(f"  Total files processed: {report['summary']['total_files']}")
        logger.info(f"  Successfully migrated: {report['summary']['migrated_files']} ({report['summary']['success_rate']:.2f}%)")
        logger.info(f"  Skipped files: {report['summary']['skipped_files']}")
        logger.info(f"  Files with fixed timestamps: {report['summary']['fixed_files']}")
        logger.info(f"  Publications: {list(report['by_publication'].keys())}")
        
        # Output full report
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Full report written to {output_path}")
            
        return report
            
def main():
    """Main function."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Migrate HSA-ready data to a clean structure")
    parser.add_argument("--source", default="output", help="Source directory with article data")
    parser.add_argument("--target", default="output/hsa-ready", help="Target directory for HSA-ready data")
    parser.add_argument("--output", default="reports/hsa_migration.json", help="Output file for migration report")
    args = parser.parse_args()
    
    migrator = HSAMigrator(args.source, args.target)
    success = migrator.migrate()
    
    if success:
        migrator.generate_report(args.output)
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 