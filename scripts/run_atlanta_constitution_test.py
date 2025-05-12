#!/usr/bin/env python3
"""
Atlanta Constitution Test Runner

This script provides a unified way to test the StoryDredge pipeline with
the Atlanta Constitution newspaper collection. It combines dataset preparation,
testing, and pipeline running into a single command.

Usage:
  python scripts/run_atlanta_constitution_test.py --prepare --test --run-pipeline
"""

import os
import sys
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import time
import json

# Ensure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.prepare_atlanta_constitution_dataset import prepare_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("atlanta_test_runner")


def run_tests(issues_file: Path = None):
    """Run the Atlanta Constitution tests"""
    logger.info("Running Atlanta Constitution tests...")
    
    cmd = ["python", "-m", "pytest", "tests/test_pipeline/test_atlanta_constitution.py", "-v"]
    
    # Run the tests
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Tests completed successfully")
        logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Tests failed with exit code: {e.returncode}")
        logger.error(e.stderr)
        return False


def run_pipeline(issues_file: Path, workers: int = None, output_dir: str = None, benchmark: bool = False):
    """Run the pipeline with the Atlanta Constitution issues file"""
    if not issues_file.exists():
        logger.error(f"Issues file not found: {issues_file}")
        return False
    
    logger.info(f"Running pipeline with issues file: {issues_file}")
    
    # Build command
    cmd = ["python", "pipeline/main.py", "--issues-file", str(issues_file)]
    
    if workers:
        cmd.extend(["--workers", str(workers)])
    
    if output_dir:
        cmd.extend(["--output-dir", output_dir])
    
    if benchmark:
        cmd.append("--benchmark")
    
    # Run the pipeline
    try:
        start_time = time.time()
        result = subprocess.run(cmd, check=True)
        elapsed_time = time.time() - start_time
        
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        logger.info(f"Pipeline completed successfully in {int(hours)}h {int(minutes)}m {int(seconds)}s")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Pipeline failed with exit code: {e.returncode}")
        return False


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description="Test the StoryDredge pipeline with the Atlanta Constitution dataset"
    )
    
    # Dataset preparation options
    parser.add_argument("--prepare", action="store_true",
                      help="Prepare the Atlanta Constitution dataset")
    parser.add_argument("--start-date", default="1922-01-01",
                      help="Start date for issues (default: 1922-01-01)")
    parser.add_argument("--end-date", default=None,
                      help="End date for issues (default: None)")
    parser.add_argument("--sample-size", type=int, default=5,
                      help="Maximum number of issues to include (default: 5)")
    parser.add_argument("--output-dir", default="data/atlanta-constitution",
                      help="Directory to save the dataset")
    
    # Testing options
    parser.add_argument("--test", action="store_true",
                      help="Run the Atlanta Constitution tests")
    
    # Pipeline options
    parser.add_argument("--run-pipeline", action="store_true",
                      help="Run the pipeline with the prepared dataset")
    parser.add_argument("--workers", type=int, default=None,
                      help="Number of parallel workers for the pipeline")
    parser.add_argument("--pipeline-output", default="output",
                      help="Output directory for the pipeline")
    parser.add_argument("--benchmark", action="store_true",
                      help="Run benchmarks after pipeline processing")
    
    # Issues file option (if not preparing a new dataset)
    parser.add_argument("--issues-file", default=None,
                      help="Use an existing issues file instead of preparing a new one")
    
    args = parser.parse_args()
    
    issues_file_path = None
    
    # Prepare the dataset if requested
    if args.prepare:
        logger.info(f"Preparing Atlanta Constitution dataset from {args.start_date}")
        issues_file_path, issues = prepare_dataset(
            start_date=args.start_date,
            end_date=args.end_date,
            sample_size=args.sample_size,
            output_dir=args.output_dir
        )
        
        if not issues_file_path:
            logger.error("Failed to prepare dataset")
            sys.exit(1)
    elif args.issues_file:
        # Use existing issues file
        issues_file_path = Path(args.issues_file)
        if not issues_file_path.exists():
            logger.error(f"Issues file not found: {issues_file_path}")
            sys.exit(1)
        logger.info(f"Using existing issues file: {issues_file_path}")
    
    # Run tests if requested
    if args.test:
        if not run_tests():
            logger.error("Tests failed")
            sys.exit(1)
    
    # Run the pipeline if requested
    if args.run_pipeline:
        if not issues_file_path:
            logger.error("No issues file available. Use --prepare or --issues-file options.")
            sys.exit(1)
        
        if not run_pipeline(
            issues_file=issues_file_path,
            workers=args.workers,
            output_dir=args.pipeline_output,
            benchmark=args.benchmark
        ):
            logger.error("Pipeline failed")
            sys.exit(1)
    
    logger.info("All operations completed successfully")


if __name__ == "__main__":
    main() 