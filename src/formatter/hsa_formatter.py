"""
HSA Formatter Module

This module transforms classified articles into HSA-ready JSON format,
validates them against the required schema, and organizes them into
the appropriate directory structure.

Features:
- Article validation against HSA schema
- Timestamp formatting standardization
- Output organization by date (YYYY/MM/DD)
- Proper field mapping from classified articles to HSA format
- JSON output formatting with configurable pretty printing
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Set
from pathlib import Path
from datetime import datetime

from src.utils.errors import ValidationError
from src.utils.config import get_config_manager


class HSAFormatter:
    """
    Formats classified articles into HSA-ready JSON format.
    
    This class handles the final stage of the pipeline, transforming
    classified articles into the format required by the Human Story
    Atlas (HSA) system and organizing them by date.
    """
    
    # Define the required fields for HSA output
    REQUIRED_FIELDS = {
        "headline", "body", "tags", "section", "timestamp",
        "publication", "source_issue", "source_url"
    }
    
    # Define valid section values
    VALID_SECTIONS = {
        "news", "sports", "business", "entertainment", "opinion",
        "local", "national", "international", "politics", "science",
        "health", "technology", "education", "weather", "obituaries",
        "lifestyle", "culture", "arts", "food", "travel", "other"
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the HSAFormatter.
        
        Args:
            output_dir: Directory for storing HSA-ready output. If None,
                        defaults to "output/hsa-ready"
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load()
        self.config = config_manager.config.formatter
        
        # Set output directory
        self.output_dir = Path(output_dir) if output_dir else Path("output/hsa-ready")
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.logger.info(f"HSA Formatter initialized with output directory: {self.output_dir}")
    
    def validate_article(self, article: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an article against HSA requirements.
        
        Args:
            article: The article to validate
            
        Returns:
            A tuple containing:
            - bool: True if valid, False otherwise
            - List[str]: List of error messages if invalid
        """
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in article or not article[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate section if present
        if "section" in article and article["section"] not in self.VALID_SECTIONS:
            errors.append(f"Invalid section: {article['section']}. Must be one of: {', '.join(self.VALID_SECTIONS)}")
        
        # Validate tags if present
        if "tags" in article and not isinstance(article["tags"], list):
            errors.append("Tags must be a list")
        
        # Validate timestamp if present
        if "timestamp" in article:
            try:
                # Just test if it can be formatted
                self.format_timestamp(article["timestamp"])
            except ValueError:
                errors.append(f"Invalid timestamp format: {article['timestamp']}")
        
        return len(errors) == 0, errors
    
    def format_timestamp(self, timestamp: str) -> str:
        """
        Format the timestamp in ISO 8601 format with UTC timezone.
        
        Args:
            timestamp: The timestamp string to format
            
        Returns:
            Formatted timestamp string in the format "YYYY-MM-DDTHH:MM:SS.000Z"
        """
        # Handle already correctly formatted timestamps
        if timestamp.endswith("Z") and "T" in timestamp:
            return timestamp
        
        try:
            # Try to parse the timestamp
            if " " in timestamp:
                # Assume format is "YYYY-MM-DD HH:MM:SS"
                dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            else:
                # Assume format is "YYYY-MM-DD"
                dt = datetime.strptime(timestamp, "%Y-%m-%d")
            
            # Format in ISO 8601 format
            return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
        except ValueError:
            # If parsing fails, use a default date
            self.logger.warning(f"Invalid timestamp format: {timestamp}, using current year with default month/day")
            year = datetime.now().year
            return f"{year}-01-01T00:00:00.000Z"
    
    def get_output_path(self, article: Dict[str, Any]) -> Path:
        """
        Determine the output path for an article based on its timestamp.
        
        Args:
            article: The article to get the path for
            
        Returns:
            Path object for where the article should be saved
        """
        # Format timestamp if not already in the right format
        if "timestamp" not in article:
            self.logger.warning("Article has no timestamp, using default")
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            timestamp = self.format_timestamp(article["timestamp"])
        
        # Extract date components from timestamp
        date_part = timestamp.split("T")[0]
        year, month, day = date_part.split("-")
        
        # Create directory structure: YYYY/MM/DD/
        output_dir = self.output_dir / year / month / day
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Create a unique filename based on headline and timestamp
        headline = article.get("headline", "untitled")
        headline_slug = headline.lower().replace(" ", "-")[:50]
        headline_slug = ''.join(c for c in headline_slug if c.isalnum() or c == '-')
        
        # Generate a unique filename
        filename = f"{headline_slug}-{int(datetime.now().timestamp())}.json"
        return output_dir / filename
    
    def format_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format an article to conform to HSA standards.
        
        Args:
            article: The article to format
            
        Returns:
            A new dictionary with properly formatted HSA fields
        """
        # Create a new dictionary for HSA output
        hsa_article = {}
        
        # Copy required fields
        for field in ["headline", "body", "section", "byline", "dateline"]:
            if field in article:
                hsa_article[field] = article[field]
        
        # Handle special fields with transformation
        
        # Tags
        hsa_article["tags"] = article.get("tags", [])
        
        # Timestamp - format to standard format
        if "date" in article:
            hsa_article["timestamp"] = self.format_timestamp(article["date"])
        elif "timestamp" in article:
            hsa_article["timestamp"] = self.format_timestamp(article["timestamp"])
        else:
            # Default to current date if no date/timestamp is provided
            hsa_article["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        # Source information
        hsa_article["publication"] = article.get("publication", "Unknown")
        hsa_article["source_issue"] = article.get("source_issue", "Unknown")
        hsa_article["source_url"] = article.get("source_url", "")
        
        # Ensure section has a valid value
        if "section" not in hsa_article or hsa_article["section"] not in self.VALID_SECTIONS:
            hsa_article["section"] = "other"
        
        # Convert empty tag array to ensure valid JSON
        if not hsa_article["tags"]:
            hsa_article["tags"] = []
        
        return hsa_article
    
    def save_article(self, article: Dict[str, Any]) -> Optional[Path]:
        """
        Save an article to its appropriate output location.
        
        Args:
            article: The article to save
            
        Returns:
            Path to the saved file, or None if validation failed
        """
        # First, format the article
        formatted_article = self.format_article(article)
        
        # Validate the formatted article
        valid, errors = self.validate_article(formatted_article)
        if not valid:
            error_msg = "; ".join(errors)
            self.logger.error(f"Article validation failed: {error_msg}")
            return None
        
        # Determine output path
        output_path = self.get_output_path(formatted_article)
        
        # Save the article
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if self.config.pretty_print:
                    json.dump(formatted_article, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(formatted_article, f, ensure_ascii=False)
            
            self.logger.info(f"Saved article to {output_path}")
            return output_path
        
        except Exception as e:
            self.logger.error(f"Error saving article: {e}")
            return None
    
    def process_batch(self, articles: List[Dict[str, Any]]) -> List[Path]:
        """
        Process a batch of articles.
        
        Args:
            articles: List of articles to process
            
        Returns:
            List of paths to the saved files (successful saves only)
        """
        self.logger.info(f"Processing batch of {len(articles)} articles")
        
        results = []
        for i, article in enumerate(articles):
            result = self.save_article(article)
            if result:
                results.append(result)
        
        self.logger.info(f"Successfully processed {len(results)} of {len(articles)} articles")
        return results
    
    def process_directory(self, input_dir: str, recursive: bool = False) -> List[Path]:
        """
        Process all JSON files in a directory.
        
        Args:
            input_dir: Directory containing article JSON files
            recursive: Whether to recursively process subdirectories
            
        Returns:
            List of paths to the saved files (successful saves only)
        """
        input_path = Path(input_dir)
        if not input_path.exists() or not input_path.is_dir():
            self.logger.error(f"Invalid input directory: {input_dir}")
            return []
        
        self.logger.info(f"Processing articles from directory: {input_dir}")
        
        results = []
        pattern = "**/*.json" if recursive else "*.json"
        
        for file_path in input_path.glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        article = json.load(f)
                    
                    result = self.save_article(article)
                    if result:
                        results.append(result)
                
                except Exception as e:
                    self.logger.error(f"Error processing file {file_path}: {e}")
        
        self.logger.info(f"Successfully processed {len(results)} articles from {input_dir}")
        return results 