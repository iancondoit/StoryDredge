#!/usr/bin/env python3
"""
run_classification.py - Process already-split articles through the classification step

This script takes a list of issue IDs and runs their articles through the classifier.
It assumes the articles have already been split and are located in the output directory.
"""

import os
import sys
import json
import logging
import argparse
import re
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.classifier.article_classifier import ArticleClassifier
from src.utils.config import get_config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def classify_issue(issue_id: str, output_dir: Path) -> bool:
    """
    Process a single issue's articles through classification.
    
    Args:
        issue_id: The archive.org identifier for the newspaper issue or path to the issue directory
        output_dir: Base output directory
        
    Returns:
        True if classification was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Define paths
    # Check if issue_id is already a path
    if os.path.sep in issue_id or issue_id.startswith('output/'):
        # If issue_id is a path, check if it's already in the new structure
        if "hsa-ready" in issue_id:
            issue_dir = Path(issue_id)
        else:
            # Convert old path structure to new structure
            # Example: "output/atlanta-constitution/1922/01/04" -> "output/hsa-ready/atlanta-constitution/1922/01/04"
            parts = Path(issue_id).parts
            if len(parts) >= 5 and parts[0] == "output":
                # Extract publication, year, month, day
                publication = parts[1]
                year, month, day = parts[2:5]
                issue_dir = Path("output/hsa-ready") / publication / year / month / day
            else:
                logger.warning(f"Cannot determine structure for path: {issue_id}, using as-is")
                issue_dir = Path(issue_id)
    else:
        # If issue_id is not a path, use it to construct the path in the new structure
        # Parse issue_id to extract date and publication
        parts = issue_id.split("_")
        if len(parts) >= 3 and re.match(r'^\d{4}-\d{2}-\d{2}', parts[2]):
            publication = parts[1]
            date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', parts[2])
            if date_match:
                year, month, day = date_match.groups()
                issue_dir = Path("output/hsa-ready") / publication / year / month / day
            else:
                logger.warning(f"Cannot parse date from: {issue_id}, using default structure")
                issue_dir = Path("output/hsa-ready/unknown") / issue_id
        else:
            logger.warning(f"Cannot parse issue ID: {issue_id}, using default structure")
            issue_dir = Path("output/hsa-ready/unknown") / issue_id
    
    # Get all article JSON files directly from the issue directory, no "articles" subdirectory
    article_files = sorted(list(issue_dir.glob("article_*.json")))
    
    if not article_files:
        logger.error(f"No article files found in {issue_dir}")
        return False
    
    logger.info(f"Found {len(article_files)} articles for issue {issue_id}")
    
    # Initialize classifier
    classifier = ArticleClassifier()
    
    # Process articles
    total_articles = len(article_files)
    
    # Simple progress display
    print(f"⠋ Processing (Overall: 100.0%)")
    
    for i, article_file in enumerate(article_files):
        try:
            # Simple progress indicator
            if (i + 1) % 5 == 0 or i == 0 or i == total_articles - 1:
                progress_pct = (i + 1) / total_articles * 100
                print(f"⠙ Classifying articles ({progress_pct:.1f}%)")
                logger.info(f"Classified {i+1}/{total_articles} articles for issue {issue_id}")
            
            # Load article
            with open(article_file, 'r', encoding='utf-8') as f:
                article = json.load(f)
            
            # Classify article
            classified_article = classifier.classify_article(article)
            
            # Save classified article back to the same file (overwrite original)
            with open(article_file, 'w', encoding='utf-8') as f:
                json.dump(classified_article, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error classifying article {article_file}: {e}")
            # Continue with next article
    
    logger.info(f"Successfully classified {total_articles} articles for issue {issue_id}")
    return True


def process_issues(issues: List[str], output_dir: Path) -> Dict[str, Any]:
    """
    Process multiple issues through the classification pipeline.
    
    Args:
        issues: List of issue IDs to process
        output_dir: Base output directory
        
    Returns:
        Dictionary with results
    """
    logger = logging.getLogger(__name__)
    
    results = {
        "successful": [],
        "failed": []
    }
    
    logger.info(f"Processing {len(issues)} issues")
    
    for issue_id in issues:
        logger.info(f"Processing issue: {issue_id}")
        
        if classify_issue(issue_id, output_dir):
            logger.info(f"Classification successful for issue {issue_id}")
            results["successful"].append(issue_id)
        else:
            logger.error(f"Classification failed for issue {issue_id}")
            results["failed"].append(issue_id)
    
    return results


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Run classification on extracted articles")
    parser.add_argument("--issue", help="Issue ID or path to process")
    parser.add_argument("--issues-file", help="File containing list of issues to process (one per line)")
    parser.add_argument("--output", default="output", help="Output directory")
    
    args = parser.parse_args()
    
    if not args.issue and not args.issues_file:
        parser.error("Either --issue or --issues-file must be specified")
    
    output_dir = Path(args.output)
    
    # Ensure config is loaded
    config_manager = get_config_manager()
    config_manager.load()
    
    if args.issue:
        # Process a single issue
        logger.info(f"Processing single issue: {args.issue}")
        result = classify_issue(args.issue, output_dir)
        sys.exit(0 if result else 1)
    
    if args.issues_file:
        # Process multiple issues from a file
        issues_file = Path(args.issues_file)
        if not issues_file.exists():
            logger.error(f"Issues file not found: {issues_file}")
            sys.exit(1)
            
        with open(issues_file, 'r', encoding='utf-8') as f:
            issues = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Loaded {len(issues)} issues from {issues_file}")
        
        results = process_issues(issues, output_dir)
        
        # Log results
        logger.info(f"Classification complete:")
        logger.info(f"  Successful: {len(results['successful'])}")
        logger.info(f"  Failed: {len(results['failed'])}")
        
        if results['failed']:
            logger.error(f"Failed issues: {', '.join(results['failed'])}")
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    main() 