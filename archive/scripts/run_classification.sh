#!/bin/bash

# run_classification.sh - Verify Ollama installation and run classification

set -e  # Exit on error

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}StoryDredge Classification Script${NC}"
echo "====================================="

# Check if Ollama is installed
echo -e "${YELLOW}Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Error: Ollama is not installed or not in PATH${NC}"
    echo "Please install Ollama from https://ollama.ai/"
    exit 1
fi
echo -e "${GREEN}Ollama is installed.${NC}"

# Check if Ollama service is running
echo -e "${YELLOW}Checking if Ollama service is running...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${RED}Error: Ollama service is not running${NC}"
    echo "Please start Ollama service with 'ollama serve' or check its status"
    exit 1
fi
echo -e "${GREEN}Ollama service is running.${NC}"

# Check if tinyllama model is pulled
echo -e "${YELLOW}Checking if tinyllama model is available...${NC}"
if ! ollama list | grep -q "tinyllama"; then
    echo -e "${YELLOW}TinyLlama model not found. Pulling it now...${NC}"
    ollama pull tinyllama
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to pull tinyllama model${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}TinyLlama model is available.${NC}"

# Run the classification script
echo -e "${YELLOW}Running classification script...${NC}"

# Default values
OUTPUT_DIR="output"
ISSUES_FILE="direct_test_results.json"  # Default to the file with the list of successful issues

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --issue)
            ISSUE="$2"
            shift 2
            ;;
        --issues-file)
            ISSUES_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Construct the command
if [ ! -z "$ISSUE" ]; then
    CMD="python scripts/run_classification.py --issue $ISSUE --output-dir $OUTPUT_DIR"
else
    CMD="python scripts/run_classification.py --issues-file $ISSUES_FILE --output-dir $OUTPUT_DIR"
fi

# Execute the command
echo "Executing: $CMD"
eval $CMD

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Classification completed successfully.${NC}"
else
    echo -e "${RED}Classification failed.${NC}"
    exit 1
fi

echo "====================================="
echo -e "${GREEN}Done!${NC}" 