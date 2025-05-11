#!/bin/bash
# StoryDredge Installation and Structure Cleanup Script

echo "=============================================="
echo "StoryDredge Installation and Structure Cleanup"
echo "=============================================="
echo

# Check if storydredge-fixed directory exists
if [ ! -d "storydredge-fixed" ]; then
    echo "Error: storydredge-fixed directory not found!"
    echo "Please run this script from the root of the StoryDredge repository."
    exit 1
fi

# Check if the user wants to proceed
echo "This script will:"
echo "1. Move all files from storydredge-fixed/ to the root directory"
echo "2. Remove duplicate directories (storydredge/ and cleaned_structure/)"
echo "3. Set up a clean, flat directory structure for StoryDredge"
echo
echo "This will modify your current directory structure."
read -p "Do you want to proceed? (y/n): " confirm
echo

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Installation canceled."
    exit 0
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p archive/raw archive/processed output/{articles,ads,classified,hsa-ready,rejected} data scripts

# Copy files from storydredge-fixed to the root
echo "Copying files from storydredge-fixed to the root..."
cp -r storydredge-fixed/scripts/* scripts/
cp -r storydredge-fixed/data/* data/ 2>/dev/null || true
cp -r storydredge-fixed/output/* output/ 2>/dev/null || true
cp -r storydredge-fixed/archive/* archive/ 2>/dev/null || true
cp storydredge-fixed/README.md . 2>/dev/null || true
cp storydredge-fixed/VERSION . 2>/dev/null || true
cp storydredge-fixed/requirements.txt . 2>/dev/null || true
cp storydredge-fixed/.env.sample . 2>/dev/null || true

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.py

# Create .env.sample file if it doesn't exist
if [ ! -f ".env.sample" ]; then
    echo "Creating .env.sample file..."
    cat > .env.sample << 'EOF'
# StoryDredge .env file
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
EOF
fi

# Copy .env if it exists in the root, but not in storydredge-fixed
if [ -f ".env" ] && [ ! -f "storydredge-fixed/.env" ]; then
    cp .env storydredge-fixed/
fi

# Run the migration script to move any remaining files from storydredge/
echo "Running migration script to move any remaining files..."
python scripts/migrate_structure.py

echo
echo "Installation completed successfully!"
echo
echo "Next steps:"
echo "1. If you don't have a .env file, copy .env.sample to .env and add your API keys:"
echo "   cp .env.sample .env"
echo
echo "2. Validate your environment by running:"
echo "   python scripts/setup.py"
echo
echo "3. Test with a small batch:"
echo "   python scripts/test_batch.py"
echo
echo "4. When everything is working, you can safely remove temporary directories:"
echo "   rm -rf storydredge/ storydredge-fixed/ cleaned_structure/"
echo

# Ask if user wants to remove temporary directories now
read -p "Do you want to clean up temporary directories now? (y/n): " cleanup
if [[ "$cleanup" == "y" || "$cleanup" == "Y" ]]; then
    echo "Cleaning up temporary directories..."
    rm -rf storydredge-fixed
    rm -rf cleaned_structure 2>/dev/null || true
    echo "Cleanup completed."
else
    echo "Temporary directories left intact for manual review."
fi

echo
echo "StoryDredge is now set up with a clean directory structure!" 