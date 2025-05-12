#!/usr/bin/env python3
"""
Process Atlanta Constitution Articles

This script processes Atlanta Constitution articles from classified directories
and converts them to HSA-ready format. It adds these to the cleaned HSA-ready directory.
"""

import os
import json
import sys
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
logger = logging.getLogger("atlanta_processor")

class AtlantaProcessor:
    """Processes Atlanta Constitution articles into HSA-ready format."""

    def __init__(self, source_base="output", target_dir="output/hsa-ready-clean"):
        """Initialize with source and target directories."""
        self.source_base = Path(source_base)
        self.target_dir = Path(target_dir)
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "by_issue": {}
        }
        
    def find_atlanta_issues(self):
        """Find Atlanta Constitution issues in the output directory."""
        issues = []
        
        for item in self.source_base.iterdir():
            if item.is_dir() and "per_atlanta-constitution" in item.name:
                issues.append(item)
                logger.info(f"Found Atlanta Constitution issue: {item.name}")
                
        return issues
        
    def process_all_issues(self):
        """Process all Atlanta Constitution issues."""
        issues = self.find_atlanta_issues()
        
        if not issues:
            logger.warning("No Atlanta Constitution issues found")
            return False
            
        logger.info(f"Found {len(issues)} Atlanta Constitution issues to process")
        
        for issue_dir in issues:
            self.process_issue(issue_dir)
            
        logger.info(f"Processing complete. Processed {self.stats['processed_files']} of {self.stats['total_files']} files.")
        return True
        
    def process_issue(self, issue_dir):
        """Process a single issue directory."""
        issue_name = issue_dir.name
        classified_dir = issue_dir / "classified"
        
        if not classified_dir.exists() or not classified_dir.is_dir():
            logger.warning(f"No classified directory found for issue {issue_name}")
            return
            
        # Extract date from issue name
        # Format: per_atlanta-constitution_YYYY-MM-DD_*
        date_match = re.search(r'per_atlanta-constitution_(\d{4}-\d{2}-\d{2})_', issue_name)
        if not date_match:
            logger.warning(f"Could not extract date from issue name: {issue_name}")
            return
            
        issue_date = date_match.group(1)
        year, month, day = issue_date.split("-")
        
        # Count files
        articles = [f for f in classified_dir.iterdir() if f.is_file() and f.name.endswith('.json')]
        self.stats["total_files"] += len(articles)
        self.stats["by_issue"][issue_name] = {
            "total": len(articles),
            "processed": 0,
            "skipped": 0
        }
        
        # Process each article
        for article_file in articles:
            success = self.process_article(article_file, "Atlanta Constitution", year, month, day, issue_name)
            
            if success:
                self.stats["processed_files"] += 1
                self.stats["by_issue"][issue_name]["processed"] += 1
            else:
                self.stats["skipped_files"] += 1
                self.stats["by_issue"][issue_name]["skipped"] += 1
                
    def process_article(self, article_file, publication, year, month, day, issue_name):
        """Process a single article file."""
        try:
            with open(article_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Create HSA-ready article
            hsa_article = {
                "headline": data.get("title", "Untitled Article"),
                "byline": None,  # Not available in source
                "dateline": None,  # Not available in source
                "body": data.get("raw_text", "").strip(),
                "section": self.determine_section(data),
                "tags": self.extract_tags(data),
                "timestamp": f"{year}-{month}-{day}T00:00:00.000Z",
                "publication": publication,
                "source_issue": f"atlanta-constitution-{year}-{month}-{day}",
                "source_url": f"https://archive.org/details/per_atlanta-constitution_{year}-{month}-{day}"
            }
            
            # Validate required fields
            if not hsa_article["headline"] or not hsa_article["body"]:
                logger.warning(f"Missing required fields in {article_file}")
                return False
                
            # Create target directory structure
            clean_publication = "atlanta_constitution"
            target_dir = self.target_dir / clean_publication / year / month / day
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a clean filename using headline or article ID
            if hsa_article["headline"]:
                # Clean headline for filename
                clean_headline = re.sub(r'[^\w\s-]', '', hsa_article["headline"])
                clean_headline = re.sub(r'\s+', '-', clean_headline)
                clean_headline = clean_headline.lower()[:50]  # Limit length
                filename = f"{year}-{month}-{day}--{clean_headline}.json"
            else:
                # Extract article ID from filename or generate a new one
                article_id = article_file.stem.split("_")[-1] if "_" in article_file.stem else str(uuid.uuid4())
                filename = f"{year}-{month}-{day}--article-{article_id}.json"
            
            # Full target path
            target_path = target_dir / filename
            
            # Write the processed file
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(hsa_article, f, indent=2)
                
            logger.info(f"Processed {article_file.name} to {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {article_file}: {e}")
            return False
            
    def determine_section(self, data):
        """Determine the section for an article."""
        if "classification" in data and "category" in data["classification"]:
            category = data["classification"]["category"].lower()
            
            # Map to HSA sections
            if category in ["news", "local", "national", "international"]:
                return "news"
            elif category in ["editorial", "opinion"]:
                return "editorial"
            elif category == "sports":
                return "sports"
            elif category in ["business", "finance", "economy"]:
                return "business"
            elif category in ["entertainment", "arts"]:
                return "entertainment"
            elif category in ["lifestyle", "living"]:
                return "lifestyle"
                
        # Default
        return "unknown"
        
    def extract_tags(self, data):
        """Extract tags from article data."""
        tags = []
        
        if "classification" in data and "metadata" in data["classification"]:
            metadata = data["classification"]["metadata"]
            
            # Add topics
            if "topic" in metadata:
                tags.append(metadata["topic"])
                
            # Add people
            if "people" in metadata and isinstance(metadata["people"], list):
                tags.extend(metadata["people"])
                
            # Add organizations
            if "organizations" in metadata and isinstance(metadata["organizations"], list):
                tags.extend(metadata["organizations"])
                
            # Add locations
            if "locations" in metadata and isinstance(metadata["locations"], list):
                tags.extend(metadata["locations"])
                
        return tags
        
    def generate_report(self, output_file=None):
        """Generate a report of the processing results."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_base": str(self.source_base),
            "target_directory": str(self.target_dir),
            "summary": {
                "total_files": self.stats["total_files"],
                "processed_files": self.stats["processed_files"],
                "skipped_files": self.stats["skipped_files"],
                "success_rate": (self.stats["processed_files"] / self.stats["total_files"] * 100) if self.stats["total_files"] > 0 else 0
            },
            "by_issue": self.stats["by_issue"]
        }
        
        # Print summary to console
        logger.info(f"Processing Summary:")
        logger.info(f"  Total files: {report['summary']['total_files']}")
        logger.info(f"  Processed files: {report['summary']['processed_files']} ({report['summary']['success_rate']:.2f}%)")
        logger.info(f"  Skipped files: {report['summary']['skipped_files']}")
        
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
    parser = argparse.ArgumentParser(description="Process Atlanta Constitution articles to HSA-ready format")
    parser.add_argument("--source", default="output", help="Source base directory with Atlanta Constitution issues")
    parser.add_argument("--target", default="output/hsa-ready-clean", help="Target directory for HSA-ready data")
    parser.add_argument("--output", default="reports/atlanta_processing.json", help="Output file for processing report")
    args = parser.parse_args()
    
    processor = AtlantaProcessor(args.source, args.target)
    success = processor.process_all_issues()
    
    if success:
        processor.generate_report(args.output)
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 