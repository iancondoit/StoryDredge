#!/bin/bash
# setup_new_structure.sh - Archive old code and set up new project structure

# Make sure archive directory exists
mkdir -p archive

# Move all project files to archive directory
echo "Moving files to archive directory..."
find . -maxdepth 1 -type f -not -path "*/\.*" -not -path "*/archive/*" -not -path "*/output/*" -not -path "*/venv/*" -not -path "*/.venv/*" -not -name "setup_new_structure.sh" | xargs -I{} mv {} archive/

# Move all project directories to archive
echo "Moving directories to archive..."
for dir in cache data logs scripts test_article tests; do
  if [ -d "$dir" ]; then
    mv "$dir" archive/
  fi
done

# Preserve and copy important files
echo "Preserving important files..."
cp archive/README.md .
cp archive/requirements.txt .
cp archive/LICENSE .

# Create new directory structure
echo "Creating new directory structure..."
mkdir -p src/{fetcher,cleaner,splitter,classifier,formatter,utils}
mkdir -p pipeline models config tests data web

# Create new README
cat > README.md << 'EOF'
# StoryDredge (Redesigned)

A streamlined pipeline for processing historical newspaper OCR using local LLMs.

This project processes newspaper issues from archive.org and extracts structured news articles for 
integration with the Human Story Atlas (HSA).

## Directory Structure
```
storydredge/
├── src/              # Core functionality modules
│   ├── fetcher/      # Archive.org downloading & caching
│   ├── cleaner/      # OCR text cleaning 
│   ├── splitter/     # Article splitting algorithms
│   ├── classifier/   # Local Llama-based classification
│   ├── formatter/    # HSA-ready output formatting
│   └── utils/        # Shared utilities
├── pipeline/         # Pipeline orchestration
├── models/           # Local model storage
├── config/           # Configuration files
├── tests/            # Unit and integration tests
└── data/             # Sample data and metadata
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Integration with Human Story Atlas
The output of this pipeline is structured JSON files that can be directly imported
into the Human Story Atlas system.
EOF

# Create updated requirements.txt for new approach
cat > requirements.txt << 'EOF'
httpx>=0.24.1
tqdm>=4.65.0
pydantic>=2.0.0
pytest>=7.0.0
loguru>=0.7.0
ollama>=0.1.0
EOF

# Create initial pipeline script
mkdir -p pipeline
cat > pipeline/main.py << 'EOF'
#!/usr/bin/env python3
"""
main.py - Main pipeline orchestration for StoryDredge

This script orchestrates the entire pipeline process:
1. Fetch OCR from archive.org
2. Clean and normalize text
3. Split into articles
4. Classify with local LLM
5. Format for Human Story Atlas
"""

import os
import sys
import argparse
from pathlib import Path


def main():
    """Main pipeline entry point."""
    parser = argparse.ArgumentParser(description="StoryDredge newspaper processing pipeline")
    parser.add_argument("--issue", help="Archive.org ID for a specific issue")
    parser.add_argument("--issues-file", help="JSON file with issues to process")
    parser.add_argument("--parallel", type=int, default=1, help="Number of issues to process in parallel")
    args = parser.parse_args()
    
    print("StoryDredge pipeline initialized")
    print("NOTE: New implementation is in progress")


if __name__ == "__main__":
    main()
EOF

# Create module structure
for dir in src/{fetcher,cleaner,splitter,classifier,formatter,utils}; do
  touch "$dir/__init__.py"
done

echo "Setup complete! New directory structure is ready."
echo "Old code is preserved in the archive/ directory."
echo "You can now begin implementing the new architecture." 