#!/usr/bin/env python3
"""
A simple script to run tests and check that the pipeline is functioning properly.
"""

import os
import sys
import subprocess
import unittest
import importlib.util

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        "openai", "python-dotenv", "requests", "tqdm", "nltk", "pytest"
    ]
    
    missing_packages = []
    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing dependencies: {', '.join(missing_packages)}")
        print("Please install using: pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check if environment is properly set up."""
    # Check if .env file exists
    if not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')):
        print("Warning: .env file not found, some features may not work")
    
    # Check if paths exist
    required_paths = [
        "storydredge/output",
        "storydredge/output/classified",
        "storydredge/output/hsa-ready",
        "storydredge/output/rejected",
        "storydredge/archive/raw",
        "storydredge/archive/processed"
    ]
    
    missing_paths = []
    for path in required_paths:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        if not os.path.exists(full_path):
            missing_paths.append(path)
    
    if missing_paths:
        print(f"Missing directory paths: {', '.join(missing_paths)}")
        print("Please create these directories")
        return False
    
    return True

def run_tests():
    """Run the tests with pytest."""
    print("Running tests...")
    result = subprocess.run(["pytest"], capture_output=True, text=True)
    
    print(result.stdout)
    if result.returncode != 0:
        print("Tests failed!")
        return False
    else:
        print("All tests passed!")
        return True

def check_pipeline():
    """Check that the pipeline scripts exist and are importable."""
    pipeline_scripts = [
        "fetch_issue.py",
        "clean_text.py",
        "split_articles.py",
        "classify_articles.py",
        "migrate_and_sanitize.py",
        "filter_and_finalize.py"
    ]
    
    missing_scripts = []
    for script in pipeline_scripts:
        script_path = os.path.join(os.path.dirname(__file__), script)
        if not os.path.exists(script_path):
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    "storydredge", "scripts", script)
            if not os.path.exists(script_path):
                missing_scripts.append(script)
    
    if missing_scripts:
        print(f"Missing pipeline scripts: {', '.join(missing_scripts)}")
        print("Please ensure all pipeline scripts are present")
        return False
    
    return True

def main():
    """Main function to run all checks."""
    print("Checking StoryDredge pipeline setup...")
    
    # Run checks
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_environment),
        ("Pipeline Scripts", check_pipeline),
        ("Tests", run_tests)
    ]
    
    all_passed = True
    for name, check_fn in checks:
        print(f"\n=== Checking {name} ===")
        if not check_fn():
            all_passed = False
    
    if all_passed:
        print("\n✅ All checks passed! The StoryDredge pipeline is ready to use.")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues before using the pipeline.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 