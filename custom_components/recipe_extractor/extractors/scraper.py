"""
Web scraper utilities for fetching recipe text from various websites.

This module handles fetching and cleaning recipe text from URLs,
with specialized scrapers for sites with poor HTML structure.
"""
import json
import logging
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)


def _fetch_voresmad_recipe(url: str) -> str:
    """Specialized scraper for voresmad.dk recipes.
    
    This site has poor HTML structure with ingredients concatenated together,
    so we need special handling to extract them properly.
    
    Args:
        url: The URL of the voresmad.dk recipe
        
    Returns:
        Formatted recipe text with properly structured ingredients
    """
    _LOGGER.info("Using voresmad.dk specialized scraper")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract title from JSON-LD or h1
    title = "Recipe"
    json_lds = soup.find_all('script', type='application/ld+json')
    for json_ld in json_lds:
        try:
            data = json.loads(json_ld.string)
            if isinstance(data, dict) and data.get('@type') == 'Recipe':
                title = data.get('name', title)
                break
        except:
            pass
    
    parts = [f"Recipe: {title}", ""]
    
    # Find the "Det skal du bruge" section
    ingredients_header = soup.find(string=lambda text: text and 'Det skal du bruge' in text)
    
    if ingredients_header:
        parts.append("Ingredients:")
        
        # Get the parent element
        header_elem = ingredients_header.parent
        
        # Look for the next siblings that contain ingredients
        current = header_elem.find_next_sibling()
        
        # Skip servings header
        if current and 'personer' in current.get_text().lower():
            current = current.find_next_sibling()
        
        # Process the paragraph(s) containing ingredients
        current_group = None
        
        while current:
            # Stop when we hit the next major section
            text_preview = current.get_text()[:100].lower()
            if any(marker in text_preview for marker in ['sådan gør', 'tilbehør', 'fremgangsmåde']):
                break
            
            if current.name == 'p':
                for element in current.descendants:
                    if element.name == 'strong':
                        # This is a group header
                        current_group = element.get_text().strip()
                        if current_group:
                            parts.append(f"\n{current_group}:")
                    elif element.name == 'br':
                        continue
                    elif isinstance(element, str):
                        line = element.strip()
                        if line and len(line) > 2:
                            # Skip group headers that appear as text
                            if current_group and line == current_group:
                                continue
                            # This is an ingredient line
                            parts.append(f"  - {line}")
            
            current = current.find_next_sibling()
    
    result = '\n'.join(parts)
    _LOGGER.info(f"Extracted structured recipe data: {len(result)} characters")
    return result


def fetch_recipe_text(url: str) -> str:
    """Fetch and clean recipe text from a URL.
    
    Uses specialized scrapers when available for better structure preservation,
    otherwise falls back to generic text extraction.
    
    Args:
        url: The URL of the recipe website
        
    Returns:
        Cleaned recipe text
    """
    _LOGGER.info(f"Fetching recipe from: {url}")
    
    # Check for site-specific scrapers
    if 'voresmad.dk' in url:
        return _fetch_voresmad_recipe(url)
    
    # Fallback to generic text extraction
    _LOGGER.info("Using generic text extraction")
    
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
        _LOGGER.debug("Using cloudscraper for bot protection bypass")
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
            _LOGGER.warning("Received 403 Forbidden. Retrying with delay...")
            time.sleep(2)
            try:
                response = session.get(url, timeout=30, allow_redirects=True)
                response.raise_for_status()
                html = response.content
            except Exception as retry_error:
                _LOGGER.error(f"Retry failed: {retry_error}")
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
            _LOGGER.debug(f"Could not parse JSON-LD: {e}")
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
        _LOGGER.info(f"Extracted structured recipe data: {len(text)} characters")
        return text
    
    # Fallback: Look for common recipe container elements
    recipe_container = None
    for selector in ['[itemtype*="Recipe"]', '.recipe', '#recipe', 'article']:
        recipe_container = soup.select_one(selector)
        if recipe_container:
            _LOGGER.debug(f"Found recipe container: {selector}")
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
    
    # Limit text length
    if len(text) > 8000:
        _LOGGER.warning(f"Text too long ({len(text)} chars), truncating to 8000 chars")
        text = text[:8000]
    
    _LOGGER.info(f"Extracted text length: {len(text)} characters")
    return text
