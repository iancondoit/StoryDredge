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
        clean_name = re.sub(r'\s+', '-', clean_name)
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
            
            # Process all JSON files in any directory that looks like a date-based structure
            # (we're looking for article_XXXX.json files directly in date directories)
            root_path = Path(root)
            
            # Skip the hsa-ready directory if we're processing from output directory
            if "hsa-ready" in root and str(self.target_dir) in root:
                continue
                
            # Process JSON files that match our article pattern
            article_files = [f for f in files if f.endswith('.json') and f.startswith('article_')]
            
            if article_files:
                # This directory contains article files - process them
                for file in article_files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                    
                    file_path = root_path / file
                    self.migrate_file(file_path)
                
        logger.info(f"Migration complete. Migrated {self.stats['migrated_files']} of {self.stats['total_files']} files.")
        return True
        
    def extract_info_from_path(self, file_path):
        """Extract publication and date info from issue path."""
        # We'll set atlanta-constitution as the publication name
        publication = "atlanta-constitution"
        
        # Extract issue ID from path
        # Example paths:
        # output/per_atlanta-constitution_1922-01-01_54_203/articles/article_0001.json
        # output/atlanta-constitution/1922/01/01/articles/article_0001.json
        parts = file_path.parts
        issue_id = None
        
        # Try to find date information in the path
        for i, part in enumerate(parts):
            # First check for publication/year/month/day pattern
            if part == "atlanta-constitution" and i + 3 < len(parts):
                # Check if the next three parts could be year, month, day
                if re.match(r'^\d{4}$', parts[i+1]) and re.match(r'^\d{2}$', parts[i+2]) and re.match(r'^\d{2}$', parts[i+3]):
                    year = parts[i+1]
                    month = parts[i+2] 
                    day = parts[i+3]
                    # Create a consistent issue ID
                    issue_id = f"per_atlanta-constitution_{year}-{month}-{day}"
                    return publication, year, month, day, issue_id
            
            # Also check for per_ prefix pattern
            if part.startswith("per_"):
                issue_id = part
                # Extract date from issue ID
                # Example: per_atlanta-constitution_1922-01-01_54_203
                id_parts = issue_id.split("_")
                if len(id_parts) >= 3:
                    date_str = id_parts[2]
                    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
                    if match:
                        year, month, day = match.groups()
                        return publication, year, month, day, issue_id
                        
            # Also look for year/month/day directories
            elif re.match(r'^\d{4}$', part):
                # Check if this could be a year followed by month and day
                if i + 2 < len(parts) and re.match(r'^\d{2}$', parts[i+1]) and re.match(r'^\d{2}$', parts[i+2]):
                    year = part
                    month = parts[i+1]
                    day = parts[i+2]
                    # Create a consistent issue ID
                    issue_id = f"per_atlanta-constitution_{year}-{month}-{day}"
                    return publication, year, month, day, issue_id
        
        # If we can't extract date info, return None
        return None, None, None, None, None
        
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
        """Convert classified article to HSA format."""
        hsa_article = {}
        
        # Copy title/headline
        hsa_article["headline"] = article.get("title", article.get("headline", "Untitled"))
        
        # Copy raw_text/body
        hsa_article["body"] = article.get("raw_text", article.get("body", ""))
        
        # Get section - use classified category if available, default to news
        category = article.get("category", "news").lower()
        hsa_article["section"] = category
        
        # Extract tags from metadata if available
        tags = []
        if "metadata" in article and article["metadata"]:
            metadata = article["metadata"]
            
            # Add category as a tag
            if category and category not in tags:
                tags.append(category)
                
            # Add tags from metadata
            if "tags" in metadata and metadata["tags"]:
                for tag in metadata["tags"]:
                    if tag and tag not in tags:
                        tags.append(tag)
                        
            # Add entities as tags (people, organizations, locations)
            for entity_type in ["people", "organizations", "locations"]:
                if entity_type in metadata and metadata[entity_type]:
                    for entity in metadata[entity_type]:
                        if entity and entity not in tags:
                            tags.append(entity)
        
        hsa_article["tags"] = tags
        
        # Format timestamp
        timestamp = f"{year}-{month}-{day}T00:00:00.000Z"
        hsa_article["timestamp"] = timestamp
        
        # Set publication info - use just "Atlanta Constitution" without "The"
        hsa_article["publication"] = "Atlanta Constitution"
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