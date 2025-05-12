#!/usr/bin/env python3
"""
Verify Atlanta Constitution Testing

This script verifies the functionality of our Atlanta Constitution testing code
by simulating the key operations without executing the full pipeline or tests.
This is useful for checking that the scripts are properly functioning before
running full tests.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Ensure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("verify_test")

def verify_files_exist():
    """Verify that all required script files exist."""
    required_files = [
        "scripts/prepare_atlanta_constitution_dataset.py",
        "scripts/test_atlanta_constitution_direct.py",
        "scripts/run_atlanta_constitution_test.py",
        "pipeline/process_ocr.py",
        "docs/testing/atlanta_constitution_testing.md"
    ]
    
    logger.info("Verifying required files exist...")
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        return False
    
    logger.info("All required files exist.")
    return True

def verify_test_directories():
    """Verify that test directories exist."""
    test_dirs = [
        "tests/test_scripts",
        "tests/test_pipeline",
        "docs/testing"
    ]
    
    logger.info("Verifying test directories exist...")
    missing_dirs = []
    
    for dir_path in test_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        logger.error(f"Missing test directories: {', '.join(missing_dirs)}")
        return False
    
    logger.info("All test directories exist.")
    return True

def verify_output_directories():
    """Verify that output directories exist or can be created."""
    output_dirs = [
        "output",
        "data/atlanta-constitution",
        "temp_downloads"
    ]
    
    logger.info("Verifying output directories...")
    
    for dir_path in output_dirs:
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory verified: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory {dir_path}: {e}")
            return False
    
    return True

def verify_curl_functionality():
    """Verify that curl is available and can follow redirects."""
    import subprocess
    
    logger.info("Verifying curl functionality...")
    
    try:
        # Check curl version
        result = subprocess.run(
            ["curl", "--version"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        logger.info(f"Curl version: {result.stdout.splitlines()[0]}")
        
        # Check if curl works with a simple URL (don't check for HTTP 200 specifically)
        test_url = "https://example.com"
        result = subprocess.run(
            ["curl", "-L", "-s", "-I", test_url],
            check=True, 
            capture_output=True, 
            text=True
        )
        
        # Just check that we got some response headers
        if result.stdout.strip():
            logger.info("Curl is working correctly.")
            return True
        else:
            logger.warning("Curl didn't return any response headers.")
            return False
        
    except subprocess.CalledProcessError:
        logger.error("Curl command failed.")
        return False
    except FileNotFoundError:
        logger.error("Curl not found on the system.")
        return False

def verify_test_script_imports():
    """Verify that the test scripts can be imported without errors."""
    logger.info("Verifying test script imports...")
    
    try:
        # Try importing key components from the scripts
        from scripts.test_atlanta_constitution_direct import download_ocr_with_curl
        from scripts.prepare_atlanta_constitution_dataset import prepare_dataset
        from pipeline.process_ocr import process_ocr
        
        logger.info("Successfully imported test script components.")
        return True
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting verification of Atlanta Constitution testing...")
    
    # Create a summary of results
    results = {
        "files_exist": verify_files_exist(),
        "test_directories": verify_test_directories(),
        "output_directories": verify_output_directories(),
        "curl_functionality": verify_curl_functionality(),
        "test_script_imports": verify_test_script_imports()
    }
    
    # Print summary
    logger.info("\n" + "="*50)
    logger.info("VERIFICATION SUMMARY")
    logger.info("="*50)
    
    all_success = True
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test.replace('_', ' ').title(): <25}: {status}")
        all_success = all_success and result
    
    logger.info("="*50)
    logger.info(f"Overall Result: {'✅ PASS' if all_success else '❌ FAIL'}")
    logger.info("="*50)
    
    # Save results
    results["timestamp"] = datetime.now().isoformat()
    with open("verification_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to verification_results.json")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main()) 