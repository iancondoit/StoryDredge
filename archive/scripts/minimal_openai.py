#!/usr/bin/env python3
"""
minimal_openai.py - Minimal implementation using httpx to call OpenAI API directly
"""

import os
import json
import time
import httpx

def process_article(article_path, output_dir=None):
    print(f"Processing article: {article_path}")
    
    # Load API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set or empty")
        print("Please set it with: export OPENAI_API_KEY=your_key")
        return None
    
    # Load the article
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            article = json.load(f)
        print(f"Article loaded: {article.get('title', 'Untitled')}")
    except Exception as e:
        print(f"Error loading article: {e}")
        return None
    
    # Prepare output directory
    if not output_dir:
        output_dir = os.path.dirname(article_path)
    
    # Extract filename without extension
    filename = os.path.basename(article_path)
    filename_no_ext = os.path.splitext(filename)[0]
    
    # Prepare the prompt
    raw_text = article.get('raw_text', '')
    if not raw_text:
        print("Error: No raw_text found in article")
        return None
    
    print(f"Text length: {len(raw_text)}")
    
    prompt = f"""
You are an expert in processing old newspaper articles. Given the raw OCR text of an article, extract structured metadata.

Return a JSON object with the following keys:

- headline (string): The title of the article.
- byline (string, optional): The name of the writer or editor.
- dateline (string, optional): A city and date header like "SAN ANTONIO, AUG. 14 —"
- body (string): The full cleaned article text.
- section (string): One of: "news", "ad", "editorial", "classified", "unknown".
- tags (array of strings): Optional keywords that describe the story.

Example input:
---
{raw_text[:500]}... (truncated)
---
"""
    
    # Prepare the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }
    
    # Make the API call
    print("Calling OpenAI API...")
    start_time = time.time()
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code}, {response.text}")
                return None
            
            result = response.json()
            elapsed_time = time.time() - start_time
            print(f"API call completed in {elapsed_time:.2f} seconds")
            
    except Exception as e:
        print(f"Error calling API: {e}")
        return None
    
    # Extract and parse the response
    try:
        content = result["choices"][0]["message"]["content"]
        extracted = json.loads(content)
        print("Successfully parsed response")
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None
    
    # Merge with original metadata
    final_result = {
        **extracted,
        "timestamp": article.get("timestamp", ""),
        "publication": article.get("publication", ""),
        "source_issue": article.get("source_issue", ""),
        "source_url": article.get("source_url", "")
    }
    
    # Save the result
    output_filename = f"minimal_classified_{filename_no_ext}.json"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        print(f"Result saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving result: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        article_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        process_article(article_path, output_dir)
    else:
        print("Usage: python minimal_openai.py <article_path> [output_dir]")
        sys.exit(1) 