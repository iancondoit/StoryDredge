#!/usr/bin/env python3
"""
run_classification.py - Process already-split articles through the classification step

This script takes a list of issue IDs and runs their articles through the classifier.
It assumes the articles have already been split and are located in the output directory.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.classifier.article_classifier import ArticleClassifier
from src.utils.config import get_config_manager


def setup_logging():
    """Configure logging for the script."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "classification.log"),
            logging.StreamHandler()
        ]
    )


def classify_issue(issue_id: str, output_dir: Path) -> bool:
    """
    Process a single issue's articles through classification.
    
    Args:
        issue_id: The archive.org identifier for the newspaper issue
        output_dir: Base output directory
        
    Returns:
        True if classification was successful, False otherwise
    """
    logger = logging.getLogger(__name__)
    
    # Define paths
    issue_dir = output_dir / issue_id
    articles_dir = issue_dir / "articles"
    classified_dir = issue_dir / "classified"
    
    # Check if articles directory exists
    if not articles_dir.exists():
        logger.error(f"Articles directory not found for issue {issue_id}")
        return False
    
    # Create classified directory if it doesn't exist
    classified_dir.mkdir(exist_ok=True)
    
    # Initialize the classifier
    classifier = ArticleClassifier()
    
    try:
        # Find all article files
        article_files = list(articles_dir.glob("article_*.json"))
        
        if not article_files:
            logger.warning(f"No article files found for issue {issue_id}")
            return False
        
        logger.info(f"Found {len(article_files)} articles for issue {issue_id}")
        
        # Process articles in batches for improved performance
        batch_size = 5  # Process 5 articles at a time
        total_articles = len(article_files)
        
        for i in range(0, total_articles, batch_size):
            batch_files = article_files[i:i+batch_size]
            batch_articles = []
            
            # Load articles for this batch
            for article_file in batch_files:
                try:
                    with open(article_file, "r", encoding="utf-8") as f:
                        article = json.load(f)
                    
                    # Store the filename with the article for later saving
                    article["_file_name"] = article_file.name
                    batch_articles.append(article)
                except Exception as e:
                    logger.error(f"Error reading article {article_file.name}: {e}")
            
            # Classify the batch
            if batch_articles:
                try:
                    # Use batch classification if available
                    classified_articles = classifier.classify_batch(batch_articles)
                    
                    # Save the classified articles
                    for classified_article in classified_articles:
                        # Get the original filename
                        file_name = classified_article.pop("_file_name", f"article_{i}.json")
                        
                        # Save the classified article
                        output_file = classified_dir / file_name
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(classified_article, f, indent=2)
                except Exception as e:
                    logger.error(f"Error batch processing articles: {e}")
                    # If batch processing fails, fall back to individual processing
                    for article in batch_articles:
                        try:
                            file_name = article.pop("_file_name", f"article_{i}.json")
                            classified_article = classifier.classify_article(article)
                            
                            output_file = classified_dir / file_name
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(classified_article, f, indent=2)
                        except Exception as inner_e:
                            logger.error(f"Error processing individual article: {inner_e}")
            
            # Log progress periodically
            current_progress = min(i + batch_size, total_articles)
            logger.info(f"Classified {current_progress}/{total_articles} articles for issue {issue_id}")
        
        logger.info(f"Successfully classified {len(article_files)} articles for issue {issue_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error classifying articles for issue {issue_id}: {e}")
        return False


def classify_issues(issue_ids: List[str], output_dir: Path) -> Dict[str, Any]:
    """
    Classify articles for multiple issues.
    
    Args:
        issue_ids: List of issue identifiers
        output_dir: Output directory path
        
    Returns:
        Dictionary with results summary
    """
    logger = logging.getLogger(__name__)
    
    # Track results
    results = {
        "successful": [],
        "failed": []
    }
    
    # Process each issue
    start_time = time.time()
    total_issues = len(issue_ids)
    
    for i, issue_id in enumerate(issue_ids):
        logger.info(f"Processing issue {i+1}/{total_issues}: {issue_id}")
        
        if classify_issue(issue_id, output_dir):
            results["successful"].append(issue_id)
        else:
            results["failed"].append(issue_id)
        
        # Log progress
        logger.info(f"Completed {i+1}/{total_issues} issues")
    
    # Calculate processing time
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Complete results
    results["total_issues"] = total_issues
    results["processing_time"] = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    logger.info(f"Classification completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
    logger.info(f"Processing time: {results['processing_time']}")
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process articles through classification")
    parser.add_argument("--issue", help="Single issue ID to process")
    parser.add_argument("--issues-file", help="JSON file with issue IDs")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize configuration
    config_manager = get_config_manager()
    config_manager.load()
    
    output_dir = Path(args.output_dir)
    
    if args.issue:
        # Process a single issue
        logger.info(f"Processing single issue: {args.issue}")
        success = classify_issue(args.issue, output_dir)
        logger.info(f"Classification {'successful' if success else 'failed'} for issue {args.issue}")
        
    elif args.issues_file:
        # Process multiple issues
        try:
            with open(args.issues_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if isinstance(data, list):
                issue_ids = data
            elif isinstance(data, dict) and "issues" in data:
                issue_ids = data["issues"]
            elif isinstance(data, dict) and "successful" in data:
                issue_ids = data["successful"]
            else:
                logger.error("Invalid issues file format")
                sys.exit(1)
                
            logger.info(f"Processing {len(issue_ids)} issues from {args.issues_file}")
            results = classify_issues(issue_ids, output_dir)
            
            # Save results
            results_file = Path("classification_results.json")
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"Results saved to {results_file}")
                
        except Exception as e:
            logger.error(f"Error processing issues from file: {e}")
            sys.exit(1)
            
    else:
        parser.print_help()
        logger.error("No input specified")


if __name__ == "__main__":
    main() 