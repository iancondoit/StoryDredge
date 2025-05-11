#!/usr/bin/env python3
"""
version.py - Version information for StoryDredge

This module provides version information and utility functions
for the StoryDredge newspaper processing system.
"""

import os
import json
from pathlib import Path

# Version information
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

# Build information
BUILD_DATE = "2025-04-30"
BUILD_STATUS = "release"  # dev, alpha, beta, release

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_version():
    """Return the current version string."""
    return VERSION

def get_version_tuple():
    """Return the current version as a tuple of (major, minor, patch)."""
    return (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

def get_build_info():
    """Return build information as a dictionary."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "status": BUILD_STATUS
    }

def print_version_info():
    """Print version information to the console."""
    print(f"StoryDredge v{VERSION} ({BUILD_STATUS})")
    print(f"Build date: {BUILD_DATE}")
    print(f"Project root: {PROJECT_ROOT}")

def save_version_info():
    """Save version information to a JSON file."""
    version_file = PROJECT_ROOT / "version.json"
    
    version_info = {
        "name": "StoryDredge",
        "version": VERSION,
        "major": VERSION_MAJOR,
        "minor": VERSION_MINOR,
        "patch": VERSION_PATCH,
        "build_date": BUILD_DATE,
        "status": BUILD_STATUS
    }
    
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2)
    
    print(f"Version information saved to {version_file}")

if __name__ == "__main__":
    # If run directly, display version information
    print_version_info()
    
    # Also save version info to JSON
    save_version_info() 