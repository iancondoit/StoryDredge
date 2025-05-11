#!/usr/bin/env python3
"""
setup.py - Setup script for StoryDredge

Usage:
    python setup.py

This script validates the environment, API keys, and creates necessary directories 
for the StoryDredge pipeline.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import requests
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('setup')

# Load environment variables
load_dotenv()

# Project paths - use consistent paths relative to the project root
# PROJECT_ROOT is the parent of the scripts directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "archive"
RAW_DIR = ARCHIVE_DIR / "raw"
PROCESSED_DIR = ARCHIVE_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
ARTICLES_DIR = OUTPUT_DIR / "articles" 
CLASSIFIED_DIR = OUTPUT_DIR / "classified"
ADS_DIR = OUTPUT_DIR / "ads"
HSA_READY_DIR = OUTPUT_DIR / "hsa-ready"
REJECTED_DIR = OUTPUT_DIR / "rejected"
DATA_DIR = PROJECT_ROOT / "data"

# Required environment variables
REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "DEFAULT_PUBLICATION"
]

def create_directories():
    """Create all necessary directories for the pipeline."""
    directories = [
        RAW_DIR,
        PROCESSED_DIR,
        OUTPUT_DIR,
        ARTICLES_DIR,
        CLASSIFIED_DIR,
        ADS_DIR,
        HSA_READY_DIR,
        REJECTED_DIR,
        DATA_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    return True

def check_env_variables():
    """Check for required environment variables."""
    missing_vars = []
    
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please create a .env file with the required variables.")
        return False
    
    return True

def test_openai_api():
    """Test the OpenAI API connection."""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! This is a test from StoryDredge setup."}
        ],
        "max_tokens": 10
    }
    
    try:
        logger.info("Testing OpenAI API connection...")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10.0
        )
        
        if response.status_code == 200:
            logger.info("OpenAI API connection successful!")
            # Try to get rate limits from headers
            rate_limit = response.headers.get("x-ratelimit-limit-requests")
            if rate_limit:
                logger.info(f"OpenAI rate limit: {rate_limit} requests per minute")
            return True
        else:
            logger.error(f"OpenAI API error: {response.status_code}, {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing OpenAI API: {e}")
        return False

def create_sample_index_file():
    """Create a sample index file if it doesn't exist."""
    index_file = DATA_DIR / "index.json"
    
    if not index_file.exists():
        sample_data = {
            "processed_issues": []
        }
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2)
        
        logger.info(f"Created sample index file: {index_file}")
    
    return True

def create_sample_env_file():
    """Create a sample .env file if it doesn't exist."""
    env_file = PROJECT_ROOT / ".env.sample"
    
    if not env_file.exists():
        sample_content = """# StoryDredge .env file
# Copy this file to .env and fill in your values

# OpenAI API settings
OPENAI_API_KEY=your_api_key_here
OPENAI_RATE_LIMIT=20  # Requests per minute

# Default publication name (used when creating new articles)
DEFAULT_PUBLICATION=San Antonio Express-News

# Archive.org settings (optional)
ARCHIVE_ORG_ACCESS_KEY=your_access_key  # Optional, for increased rate limits
ARCHIVE_ORG_SECRET_KEY=your_secret_key  # Optional, for increased rate limits

# Output settings
MAX_ARTICLES_PER_ISSUE=0  # 0 = no limit
SKIP_SHORT_ARTICLES=true  # Skip articles with less than 100 characters
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        logger.info(f"Created sample .env file: {env_file}")
        logger.info("Please copy .env.sample to .env and update with your API keys.")
    
    return True

def print_summary():
    """Print a summary of the setup status."""
    logger.info("\n=========== StoryDredge Setup Summary ===========")
    logger.info(f"Project Directory: {PROJECT_ROOT}")
    logger.info(f"Archive Directory: {ARCHIVE_DIR}")
    logger.info(f"Output Directory: {OUTPUT_DIR}")
    logger.info(f"Default Publication: {os.getenv('DEFAULT_PUBLICATION', 'Not Set')}")
    logger.info(f"OpenAI API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not Set'}")
    
    # Print recommended next steps
    logger.info("\nRecommended Next Steps:")
    logger.info("1. Run a test issue: python scripts/fetch_issue.py <archive_id>")
    logger.info("2. Or use batch processing: python scripts/batch_process.py --issues=data/sample_issues.json")
    logger.info("=========================================\n")

def main():
    """Main function."""
    logger.info("Starting StoryDredge setup...")
    
    # Create directories
    if not create_directories():
        logger.error("Failed to create directories")
        sys.exit(1)
    
    # Check environment variables
    if not check_env_variables():
        logger.warning("Environment variables check failed, but continuing setup")
        create_sample_env_file()
    
    # Test OpenAI API
    if not test_openai_api():
        logger.warning("OpenAI API test failed, but continuing setup")
    
    # Create sample index file
    if not create_sample_index_file():
        logger.warning("Failed to create sample index file, but continuing setup")
    
    # Print summary
    print_summary()
    
    logger.info("Setup complete!")

if __name__ == "__main__":
    main() 