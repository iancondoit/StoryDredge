#!/usr/bin/env python3
"""
search_archive.py - Search for newspaper issues on Archive.org

Usage:
    python search_archive.py --query "San Antonio Express" --start-date 1977-01-01 --end-date 1977-12-31
    python search_archive.py --query "Chicago Tribune" --limit 20
    
This script searches Archive.org for newspaper issues and outputs a JSON file that can be used 
with StoryDredge's batch processing functionality.
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Search for newspaper issues on Archive.org")
    parser.add_argument("--query", help="Search query (e.g., newspaper name)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--collection", help="Specific Archive.org collection (e.g., 'townnews')")
    parser.add_argument("--list-collections", action="store_true", help="List popular newspaper collections")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of results")
    parser.add_argument("--output", default="issues.json", help="Output JSON file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed information")
    
    return parser.parse_args()

def list_newspaper_collections():
    """List popular newspaper collections on Archive.org."""
    collections = [
        {"id": "newspapers", "name": "Newspapers", "description": "All newspaper collections"},
        {"id": "us_newspapers", "name": "US Newspapers", "description": "United States newspaper archives"},
        {"id": "townnews", "name": "Small Town Newspapers", "description": "American small town papers"},
        {"id": "chictrib", "name": "Chicago Tribune", "description": "Chicago Tribune archives"},
        {"id": "sfchronicle", "name": "San Francisco Chronicle", "description": "San Francisco Chronicle archives"},
        {"id": "historicnewspapers", "name": "Historic Newspapers", "description": "Various historic newspaper collections"},
        {"id": "philippinepublications", "name": "Philippine Publications", "description": "Newspapers from the Philippines"},
        {"id": "international_newspapers", "name": "International Newspapers", "description": "Newspapers from around the world"}
    ]
    
    print("\nPopular Newspaper Collections on Archive.org:")
    print("==============================================")
    for coll in collections:
        print(f"- {coll['name']} (--collection {coll['id']})")
        print(f"  {coll['description']}")
    print()
    
    print("To browse collections directly, visit: https://archive.org/details/newspapers")
    print()

def search_archive(query=None, collection=None, start_date=None, end_date=None, limit=50):
    """
    Search Archive.org for newspaper issues.
    
    Args:
        query (str): Search query
        collection (str): Specific collection to search
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        limit (int): Maximum number of results
        
    Returns:
        list: List of issue dictionaries
    """
    base_url = "https://archive.org/advancedsearch.php"
    
    # Build query components
    components = []
    
    # Add collection filter
    if collection:
        components.append(f"collection:({collection})")
    else:
        components.append("mediatype:(texts) AND collection:(newspapers)")
    
    # Add title/query search
    if query:
        components.append(f"title:({query})")
    
    # Build date filter if provided
    if start_date:
        date_filter = f"date:[{start_date} TO "
        date_filter += end_date if end_date else "NOW"
        date_filter += "]"
        components.append(date_filter)
    
    # Join all query components
    search_query = " AND ".join(components)
    
    # Parameters for the API request
    params = {
        "q": search_query,
        "fl[]": "identifier,title,date,description,subject,collection",
        "sort[]": "date asc",
        "rows": limit,
        "page": 1,
        "output": "json"
    }
    
    print(f"Searching Archive.org for: {search_query}")
    
    # Make the API request
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        print(f"Error: Failed to search Archive.org (Status code: {response.status_code})")
        return []
    
    # Parse the response
    data = response.json()
    results = data.get("response", {}).get("docs", [])
    
    print(f"Found {len(results)} results")
    return results

def extract_publication_name(title):
    """Extract publication name from the title."""
    # Common title formats:
    # - "San Antonio Express. [volume] (San Antonio, Tex.), 1977-08-14"
    # - "Chicago Tribune (Chicago, Ill.), 1977-01-01"
    
    parts = title.split('(')
    if len(parts) > 0:
        name = parts[0].strip()
        # Remove volume info
        if '[' in name and ']' in name:
            name = name.split('[')[0].strip()
        # Remove trailing dot
        if name.endswith('.'):
            name = name[:-1].strip()
        return name
    
    return "Unknown Publication"

def extract_date(result):
    """Extract date from the result in YYYY-MM-DD format."""
    # Try to get from date field
    date = result.get("date")
    
    # If not available, try to extract from title
    if not date:
        title = result.get("title", "")
        # Look for date pattern at the end: YYYY-MM-DD
        parts = title.split()
        for part in reversed(parts):
            if len(part) == 10 and part.count('-') == 2:
                date = part
                break
    
    # Validate and standardize date format
    if date:
        try:
            # Handle ISO format (e.g., '1977-01-01T00:00:00Z')
            if 'T' in date:
                date = date.split('T')[0]
            
            # Parse the date to validate it
            dt = datetime.strptime(date, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            # Try to extract date from parentheses in title as fallback
            title = result.get("title", "")
            if "(" in title and ")" in title:
                date_part = title.split("(")[-1].split(")")[0]
                if "-" in date_part:
                    try:
                        dt = datetime.strptime(date_part, "%Y-%m-%d")
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
    
    return None

def check_ocr_availability(identifier, verbose=False):
    """
    Check if OCR text is available for a given Archive.org identifier.
    
    Args:
        identifier (str): Archive.org identifier
        verbose (bool): Whether to print detailed info about available files
        
    Returns:
        bool: True if OCR text is available, False otherwise
    """
    # Get the file listing for this item
    file_listing_url = f"https://archive.org/metadata/{identifier}/files"
    
    try:
        # Get list of files available for this item
        response = requests.get(file_listing_url, timeout=10)
        
        if response.status_code != 200:
            if verbose:
                print(f"Warning: Failed to get file listing for {identifier}")
            return False
        
        data = response.json()
        files = data.get("result", [])
        
        # Print available files if verbose
        if verbose:
            print(f"\nFiles available for {identifier}:")
            for file in files:
                print(f" - {file.get('name', 'unknown')}")
        
        # Look specifically for _djvu.txt file first (what StoryDredge uses)
        djvu_filename = f"{identifier}_djvu.txt"
        for file in files:
            filename = file.get("name", "")
            if filename == djvu_filename:
                if verbose:
                    print(f"Found primary OCR file: {filename}")
                return True
        
        # Fallback to any other OCR or text files
        for file in files:
            filename = file.get("name", "")
            if filename.endswith(".txt") or any(fmt in filename for fmt in ["ocr", "djvu", "text"]):
                if not filename.endswith((".xml", ".gz", ".json")):  # Exclude non-text formats
                    if verbose:
                        print(f"Found potential OCR file: {filename}")
                    return True
        
        return False
    
    except Exception as e:
        if verbose:
            print(f"Error checking OCR availability for {identifier}: {e}")
        return False

def process_results(results, verbose=False):
    """
    Process search results into a format suitable for StoryDredge.
    
    Args:
        results (list): Search results from Archive.org
        verbose (bool): Whether to show detailed info
        
    Returns:
        list: List of issue dictionaries for StoryDredge
    """
    issues = []
    
    print("\nChecking OCR availability for each issue...")
    
    for result in tqdm(results, desc="Checking OCR"):
        identifier = result.get("identifier")
        title = result.get("title", "")
        
        # Extract publication name
        publication = extract_publication_name(title)
        
        # Extract date
        date = extract_date(result)
        
        if identifier and date:
            # Check if OCR text is available
            has_ocr = check_ocr_availability(identifier, verbose)
            
            issue = {
                "archive_id": identifier,
                "date": date,
                "publication": publication,
                "title": title,
                "has_ocr": has_ocr
            }
            issues.append(issue)
        else:
            if verbose:
                print(f"Warning: Skipping result without required data: {result}")
    
    # Filter issues that have OCR available
    processable_issues = [issue for issue in issues if issue["has_ocr"]]
    
    print(f"\nFound {len(processable_issues)} issues with OCR text available out of {len(issues)} total")
    
    return processable_issues

def save_issues(issues, output_file):
    """Save issues to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(issues, f, indent=2)
    
    print(f"Saved {len(issues)} issues to {output_file}")

def display_results(results, verbose=False):
    """Display results in a readable format."""
    if not results:
        print("No results found.")
        return
    
    print("\nNewspaper Issues Found:")
    print("=======================")
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "Unknown Title")
        identifier = result.get("identifier", "")
        date = result.get("date", "Unknown Date")
        
        # Clean up date format
        if date and 'T' in date:
            date = date.split('T')[0]
        
        print(f"{i}. {title} ({date})")
        print(f"   ID: {identifier}")
        
        if verbose:
            # Display additional information if available
            description = result.get("description", "")
            if description:
                if isinstance(description, list):
                    description = " ".join(description)
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:100] + "..."
                print(f"   Description: {description}")
            
            # Display subjects/tags
            subjects = result.get("subject", [])
            if subjects:
                if isinstance(subjects, str):
                    subjects = [subjects]
                print(f"   Subjects: {', '.join(subjects[:5])}")
                if len(subjects) > 5:
                    print(f"            ... and {len(subjects) - 5} more")
            
            # Display collections
            collections = result.get("collection", [])
            if collections:
                if isinstance(collections, str):
                    collections = [collections]
                print(f"   Collections: {', '.join(collections[:3])}")
            
            # Display URL
            print(f"   URL: https://archive.org/details/{identifier}")
        
        print()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Show collection list if requested
    if args.list_collections:
        list_newspaper_collections()
        return
    
    # Require query or collection
    if not args.query and not args.collection:
        print("Error: Please provide either a --query or --collection parameter")
        print("Use --list-collections to see available newspaper collections")
        return
    
    # Search Archive.org
    results = search_archive(
        query=args.query,
        collection=args.collection,
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit
    )
    
    if not results:
        print("No results found.")
        return
    
    # Display results
    display_results(results, args.verbose)
    
    # Process results
    issues = process_results(results, args.verbose)
    
    if not issues:
        print("No issues with OCR text available for processing.")
        return
    
    # Save to JSON file
    save_issues(issues, args.output)
    
    print(f"\n{len(issues)} newspaper issues have been saved to {args.output}")
    print("\nTo process these issues with StoryDredge, run:")
    print(f"python storydredge/scripts/batch_process.py --issues {args.output}")
    print(f"\nOr to process a single issue, run:")
    print(f"python storydredge/scripts/fetch_issue.py <archive_id>")
    print("followed by the rest of the pipeline commands\n")

if __name__ == "__main__":
    main() 