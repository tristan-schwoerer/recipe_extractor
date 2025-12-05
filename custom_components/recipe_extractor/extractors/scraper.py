"""
Web scraper utilities for fetching recipe text from various websites.

This module handles fetching and cleaning recipe text from URLs,
with specialized scrapers for sites with poor HTML structure.
"""
import json
import time

import requests
from bs4 import BeautifulSoup


def fetch_recipe_text(url: str) -> str:
    """Fetch and clean recipe text from a URL.
    
    Uses specialized scrapers when available for better structure preservation,
    otherwise falls back to generic text extraction.
    
    Args:
        url: The URL of the recipe website
        
    Returns:
        Cleaned recipe text
    """
    
    # Try to use cloudscraper if available
    try:
        import cloudscraper
        session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
    except ImportError:
        # Fallback to requests with comprehensive headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        session = requests.Session()
        session.headers.update(headers)
    
    try:
        response = session.get(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        html = response.content
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            time.sleep(2)
            try:
                response = session.get(url, timeout=30, allow_redirects=True)
                response.raise_for_status()
                html = response.content
            except Exception as retry_error:
                raise
        else:
            raise
    
    soup = BeautifulSoup(html, features="html.parser")
    
    # Helper function to check if an item is a Recipe
    def is_recipe(item):
        if not isinstance(item, dict):
            return False
        item_type = item.get('@type')
        if isinstance(item_type, str):
            return item_type == 'Recipe'
        elif isinstance(item_type, list):
            return 'Recipe' in item_type
        return False
    
    # Check all JSON-LD scripts
    json_lds = soup.find_all('script', type='application/ld+json')
    data = None
    
    for json_ld in json_lds:
        try:
            parsed_data = json.loads(json_ld.string)
            
            if isinstance(parsed_data, list):
                data = next((item for item in parsed_data if is_recipe(item)), None)
            elif isinstance(parsed_data, dict):
                if '@graph' in parsed_data:
                    graph = parsed_data['@graph']
                    if isinstance(graph, list):
                        data = next((item for item in graph if is_recipe(item)), None)
                elif is_recipe(parsed_data):
                    data = parsed_data
            
            if data:
                break
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            continue
    
    # If we found recipe data in JSON-LD, extract it
    if data:
        parts = []
        if data.get('name'):
            parts.append(f"Recipe: {data['name']}")
        if data.get('recipeIngredient'):
            parts.append("\nIngredients:")
            for ingredient in data['recipeIngredient']:
                parts.append(f"- {ingredient}")
        if data.get('recipeInstructions'):
            parts.append("\nInstructions:")
            instructions = data['recipeInstructions']
            if isinstance(instructions, list):
                for i, step in enumerate(instructions, 1):
                    if isinstance(step, dict):
                        parts.append(f"{i}. {step.get('text', '')}")
                    else:
                        parts.append(f"{i}. {step}")
            else:
                parts.append(instructions)
        
        text = '\n'.join(parts)
        return text
    
    # Fallback: Look for common recipe container elements
    recipe_container = None
    for selector in ['[itemtype*="Recipe"]', '.recipe', '#recipe', 'article']:
        recipe_container = soup.select_one(selector)
        if recipe_container:
            break
    
    if recipe_container:
        soup = recipe_container
    
    # Remove unnecessary elements
    for element in soup(["script", "style", "nav", "header", "footer", "aside", 
                         "iframe", "noscript", "svg"]):
        element.extract()
    
    # Remove common non-recipe sections
    patterns_to_remove = ['advertisement', 'social-share', 'comment', 
                          'navigation', 'sidebar', 'newsletter',
                          'cookie-banner', 'popup', 'modal']
    if not recipe_container:
        patterns_to_remove.extend(['related', 'recommendation'])
    
    for pattern in patterns_to_remove:
        for element in soup.find_all(class_=lambda x: x and pattern in x.lower()):
            element.extract()
        for element in soup.find_all(id=lambda x: x and pattern in x.lower()):
            element.extract()
    
    # Get text with newline separators
    text = soup.get_text(separator='\n')
    
    # Clean up text
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Limit text length since otherwise we trigger the rate limiter of the free gemini models
    if len(text) > 8000:
        text = text[:8000]
    
    return text
