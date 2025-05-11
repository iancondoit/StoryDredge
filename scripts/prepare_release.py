#!/usr/bin/env python3
"""
prepare_release.py - Prepare StoryDredge for version 1.0 release

This script prepares the StoryDredge project for release by:
1. Running end-to-end tests
2. Building documentation
3. Creating a release package
4. Generating release notes
"""

import os
import sys
import subprocess
import shutil
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("release")

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_command(command, description):
    """Run a shell command and log the output."""
    logger.info(f"Running: {description}")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Command failed with exit code {process.returncode}")
            logger.error(f"Error output: {stderr}")
            return False, stderr
        
        return True, stdout
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return False, str(e)

def run_tests():
    """Run all tests including end-to-end tests."""
    logger.info("Running unit tests...")
    success, output = run_command("python run_tests.py", "Unit tests")
    if not success:
        logger.error("Unit tests failed, aborting release preparation")
        return False
    
    logger.info("Running end-to-end tests...")
    success, output = run_command("python tests/end_to_end_test.py", "End-to-end tests")
    if not success:
        logger.error("End-to-end tests failed, aborting release preparation")
        return False
    
    logger.info("All tests passed successfully!")
    return True

def build_documentation():
    """Build the documentation site."""
    logger.info("Building documentation site...")
    
    # Make sure mkdocs is installed
    run_command("pip install mkdocs mkdocs-material", "Installing mkdocs")
    
    # Build the documentation
    success, output = run_command("mkdocs build", "Building documentation")
    if not success:
        logger.error("Documentation build failed, aborting release preparation")
        return False
    
    logger.info("Documentation built successfully!")
    return True

def create_release_package():
    """Create a release package with all required files."""
    logger.info("Creating release package...")
    release_dir = Path("dist")
    release_dir.mkdir(exist_ok=True)
    
    # Define the release filename with version
    version = "1.0.0"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    release_filename = f"storydredge-{version}-{timestamp}.zip"
    release_path = release_dir / release_filename
    
    # Define directories and files to include
    include_dirs = [
        "src", "pipeline", "config", "docs/site", 
        "examples", "tests"
    ]
    
    include_files = [
        "README.md", "LICENSE", "requirements.txt", 
        "run_tests.py", "pipeline/main.py"
    ]
    
    # Exclude directories
    exclude_dirs = [
        "__pycache__", ".git", ".pytest_cache", "venv", ".venv",
        "archive", "cache", "logs", "output"
    ]
    
    # Create a zip file with the release contents
    try:
        import zipfile
        
        with zipfile.ZipFile(release_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add individual files
            for file in include_files:
                if Path(file).exists():
                    zipf.write(file, file)
            
            # Add directories recursively
            for directory in include_dirs:
                dir_path = Path(directory)
                if dir_path.exists():
                    for root, dirs, files in os.walk(dir_path):
                        # Skip excluded directories
                        dirs[:] = [d for d in dirs if d not in exclude_dirs]
                        
                        for file in files:
                            file_path = Path(root) / file
                            zipf.write(file_path, file_path)
        
        # Calculate hash for verification
        sha256_hash = hashlib.sha256()
        with open(release_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        # Create a manifest file
        manifest = {
            "name": "StoryDredge",
            "version": version,
            "release_date": datetime.now().strftime("%Y-%m-%d"),
            "package": release_filename,
            "sha256": sha256_hash.hexdigest(),
            "size": os.path.getsize(release_path)
        }
        
        with open(release_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Release package created: {release_path}")
        logger.info(f"Package size: {os.path.getsize(release_path) / (1024*1024):.2f} MB")
        logger.info(f"SHA256: {sha256_hash.hexdigest()}")
        
        return True, manifest
    
    except Exception as e:
        logger.error(f"Failed to create release package: {e}")
        return False, None

def generate_release_notes(manifest):
    """Generate release notes based on the git history."""
    if not manifest:
        return False
    
    logger.info("Generating release notes...")
    
    # Get git log since the last tag or the last 50 commits
    success, git_log = run_command(
        "git log --pretty=format:'%h - %s (%an)' -n 50", 
        "Getting git history"
    )
    
    if not success:
        logger.warning("Failed to get git history, using empty release notes")
        git_log = ""
    
    # Create release notes
    release_notes = f"""# StoryDredge {manifest['version']} Release Notes

Release Date: {manifest['release_date']}

## Overview

StoryDredge {manifest['version']} is a complete implementation of the newspaper OCR processing pipeline
with all planned features and optimizations. This release includes parallel processing capabilities,
performance optimizations, and comprehensive documentation.

## Installation

1. Download the release package: `{manifest['package']}`
2. Verify the SHA256 hash: `{manifest['sha256']}`
3. Extract the zip file
4. Follow the installation instructions in the README.md file

## Key Features

- Archive.org OCR fetching with caching
- OCR text cleaning and normalization
- Article boundary detection and extraction
- Local LLM-based article classification
- HSA-compatible JSON output
- Parallel processing for improved throughput
- Comprehensive benchmarking and optimization tools

## Release Contents

- Full source code in `src/` directory
- Pipeline orchestration scripts in `pipeline/` directory
- Configuration files in `config/` directory
- Example scripts in `examples/` directory
- Tests in `tests/` directory
- Documentation in `docs/site/` directory

## Recent Changes

{git_log}

## Known Issues

- Ollama must be installed separately for classification to work

## Next Steps

Future development will focus on:
1. CI/CD pipeline integration
2. Additional model support beyond Ollama
3. Web interface for pipeline management
4. Enhanced visualization of processing results
5. Integration with additional newspaper archives
"""
    
    # Write release notes to file
    release_notes_path = Path("dist") / f"RELEASE_NOTES_{manifest['version']}.md"
    with open(release_notes_path, "w") as f:
        f.write(release_notes)
    
    logger.info(f"Release notes generated: {release_notes_path}")
    return True

def main():
    """Main release preparation function."""
    logger.info("Starting StoryDredge 1.0 release preparation")
    
    # Make sure we're in the project root
    if not Path("src").exists() or not Path("pipeline").exists():
        logger.error("This script must be run from the project root directory")
        return 1
    
    # Step 1: Run all tests
    if not run_tests():
        return 1
    
    # Step 2: Build documentation
    if not build_documentation():
        return 1
    
    # Step 3: Create release package
    success, manifest = create_release_package()
    if not success:
        return 1
    
    # Step 4: Generate release notes
    if not generate_release_notes(manifest):
        logger.warning("Failed to generate release notes, continuing anyway")
    
    logger.info("StoryDredge 1.0 release preparation completed successfully!")
    logger.info(f"Release package is available in the 'dist' directory")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 