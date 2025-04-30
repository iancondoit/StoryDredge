#!/usr/bin/env python3
"""
migrate_structure.py - Migrate files from old nested structure to the new clean structure

Usage:
    python migrate_structure.py

This script migrates files from the old nested directory structure to the new flat structure,
organizing everything consistently.
"""

import os
import sys
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('migrate_structure')

# Project paths
OLD_ROOT = Path(__file__).resolve().parent.parent.parent
STORYDREDGE_DIR = OLD_ROOT / "storydredge"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories to migrate from old nested structure
DIRS_TO_MIGRATE = [
    ("archive", "archive"),
    ("data", "data"),
    ("output", "output"),
    ("scripts", "scripts"),
]

def ensure_target_dirs():
    """Ensure all target directories exist."""
    for _, target_rel_path in DIRS_TO_MIGRATE:
        target_path = PROJECT_ROOT / target_rel_path
        target_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {target_path}")

def migrate_files():
    """Migrate files from the old structure to the new structure."""
    # First, check if the old structure exists
    if not STORYDREDGE_DIR.exists():
        logger.warning(f"Old structure directory not found: {STORYDREDGE_DIR}")
        logger.info("Nothing to migrate!")
        return
    
    # Migrate each directory
    for source_dir, target_dir in DIRS_TO_MIGRATE:
        source_path = STORYDREDGE_DIR / source_dir
        target_path = PROJECT_ROOT / target_dir
        
        # Check if source exists
        if not source_path.exists():
            logger.warning(f"Source directory not found: {source_path}")
            continue
        
        logger.info(f"Migrating {source_path} to {target_path}")
        
        # Copy all files and directories from source to target
        for item in source_path.glob('*'):
            item_target = target_path / item.name
            
            # Skip if target already exists
            if item_target.exists():
                if item.is_file():
                    logger.warning(f"Target file already exists, skipping: {item_target}")
                    continue
                
                # For directories, we need to merge
                if item.is_dir():
                    logger.info(f"Target directory exists, merging: {item_target}")
                    merge_directories(item, item_target)
                    continue
            
            # Copy the item
            try:
                if item.is_file():
                    shutil.copy2(item, item_target)
                    logger.info(f"Copied file: {item} -> {item_target}")
                elif item.is_dir():
                    shutil.copytree(item, item_target, dirs_exist_ok=True)
                    logger.info(f"Copied directory: {item} -> {item_target}")
            except Exception as e:
                logger.error(f"Error copying {item}: {e}")

def merge_directories(source_dir, target_dir):
    """Merge two directories, copying files from source to target."""
    for item in source_dir.glob('*'):
        item_target = target_dir / item.name
        
        # Skip if target already exists and is a file
        if item.is_file() and item_target.exists():
            logger.warning(f"Target file already exists, skipping: {item_target}")
            continue
        
        # Recursively merge if both are directories
        if item.is_dir() and item_target.exists() and item_target.is_dir():
            logger.info(f"Merging directories: {item} -> {item_target}")
            merge_directories(item, item_target)
            continue
        
        # Copy the item
        try:
            if item.is_file():
                shutil.copy2(item, item_target)
                logger.info(f"Copied file: {item} -> {item_target}")
            elif item.is_dir():
                shutil.copytree(item, item_target, dirs_exist_ok=True)
                logger.info(f"Copied directory: {item} -> {item_target}")
        except Exception as e:
            logger.error(f"Error copying {item}: {e}")

def fix_all_scripts_paths():
    """Update path references in all scripts to use the new structure."""
    scripts_dir = PROJECT_ROOT / "scripts"
    
    # Find all Python files
    python_files = list(scripts_dir.glob("*.py"))
    logger.info(f"Found {len(python_files)} Python files to check for path updates")
    
    for py_file in python_files:
        fix_script_paths(py_file)

def fix_script_paths(script_path):
    """Update path references in a script to use the new structure."""
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace common path patterns
        updated_content = content
        
        # Replace "output" with "output"
        updated_content = updated_content.replace('output', 'output')
        updated_content = updated_content.replace('archive', 'archive')
        updated_content = updated_content.replace('data', 'data')
        updated_content = updated_content.replace('scripts', 'scripts')
        
        # Replace PROJECT_ROOT / "output" with PROJECT_ROOT / "output"
        updated_content = updated_content.replace('PROJECT_ROOT / "output"', 'PROJECT_ROOT / "output"')
        updated_content = updated_content.replace('PROJECT_ROOT / "archive"', 'PROJECT_ROOT / "archive"')
        updated_content = updated_content.replace('PROJECT_ROOT / "data"', 'PROJECT_ROOT / "data"')
        updated_content = updated_content.replace('PROJECT_ROOT / "scripts"', 'PROJECT_ROOT / "scripts"')
        
        # Replace PROJECT_ROOT variable with PROJECT_ROOT
        updated_content = updated_content.replace('PROJECT_ROOT = Path(__file__).resolve().parent.parent', 'PROJECT_ROOT = Path(__file__).resolve().parent.parent')
        updated_content = updated_content.replace('PROJECT_ROOT = Path(__file__).resolve().parent.parent', 'PROJECT_ROOT = Path(__file__).resolve().parent.parent')
        
        # Replace remaining PROJECT_ROOT with PROJECT_ROOT
        updated_content = updated_content.replace('PROJECT_ROOT', 'PROJECT_ROOT')
        
        # Write updated content if changes were made
        if content != updated_content:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            logger.info(f"Updated path references in: {script_path}")
    
    except Exception as e:
        logger.error(f"Error fixing paths in {script_path}: {e}")

def create_env_sample():
    """Create a sample .env file."""
    env_sample = PROJECT_ROOT / ".env.sample"
    env_file = PROJECT_ROOT / ".env"
    
    if not env_sample.exists():
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
        with open(env_sample, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        logger.info(f"Created sample .env file: {env_sample}")
    
    # Copy existing .env file if it exists
    if (OLD_ROOT / ".env").exists() and not env_file.exists():
        shutil.copy2(OLD_ROOT / ".env", env_file)
        logger.info(f"Copied existing .env file to: {env_file}")

def main():
    """Main function."""
    logger.info("Starting migration of directory structure...")
    
    # Create target directories
    ensure_target_dirs()
    
    # Migrate files from old structure to new
    migrate_files()
    
    # Fix path references in scripts
    fix_all_scripts_paths()
    
    # Create .env.sample file
    create_env_sample()
    
    logger.info("\nMigration completed!")
    logger.info("\nNext steps:")
    logger.info("1. Review the new directory structure to make sure everything was migrated correctly")
    logger.info("2. Run 'python scripts/setup.py' to validate the environment")
    logger.info("3. Run 'python scripts/test_batch.py' to test the pipeline with a small batch")

if __name__ == "__main__":
    main() 