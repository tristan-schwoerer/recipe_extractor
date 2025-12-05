#!/usr/bin/env python3
"""
Recipe Converter - Extract recipes from websites

Fetches recipes from URLs, parses the text, and extracts structured
ingredient lists using Google's LangExtract library.
"""
import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from src.extractors.recipe_extractor import RecipeExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def _fetch_voresmad_recipe(url: str) -> str:
    """Specialized scraper for voresmad.dk recipes.
    
    This site has poor HTML structure with ingredients concatenated together,
    so we need special handling to extract them properly.
    
    Args:
        url: The URL of the voresmad.dk recipe
        
    Returns:
        Formatted recipe text with properly structured ingredients
    """
    logger.info("Using voresmad.dk specialized scraper")
    
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
        # The structure is: h2 (header) -> h3 (servings) -> p (ingredients with <br/> separators)
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
            
            # The ingredients are in <p> tags with <br/> separators
            # Also look for <strong> tags which indicate group headers
            if current.name == 'p':
                # Process each line (separated by <br/>)
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
    logger.info(f"Extracted structured recipe data: {len(result)} characters")
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
    logger.info(f"Fetching recipe from: {url}")
    
    # Check for site-specific scrapers
    if 'voresmad.dk' in url:
        return _fetch_voresmad_recipe(url)
    
    # Fallback to generic text extraction
    logger.info("Using generic text extraction")
    
    # Try to use cloudscraper if available (bypasses Cloudflare and similar protections)
    try:
        import cloudscraper
        session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        logger.debug("Using cloudscraper for bot protection bypass")
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
            logger.warning("Received 403 Forbidden. Retrying with delay...")
            time.sleep(2)
            try:
                response = session.get(url, timeout=30, allow_redirects=True)
                response.raise_for_status()
                html = response.content
            except Exception as retry_error:
                logger.error(f"Retry failed: {retry_error}")
                raise
        else:
            raise
    
    soup = BeautifulSoup(html, features="html.parser")
    
    # Try to find recipe-specific content first (schema.org structured data or common recipe containers)
    recipe_container = None
    
    # Look for JSON-LD recipe data
    # Helper function to check if an item is a Recipe
    def is_recipe(item):
        if not isinstance(item, dict):
            return False
        item_type = item.get('@type')
        # @type can be a string or an array
        if isinstance(item_type, str):
            return item_type == 'Recipe'
        elif isinstance(item_type, list):
            return 'Recipe' in item_type
        return False
    
    # Check all JSON-LD scripts (some sites have multiple)
    json_lds = soup.find_all('script', type='application/ld+json')
    data = None
    
    for json_ld in json_lds:
        try:
            import json
            parsed_data = json.loads(json_ld.string)
            
            # Handle both single recipe and arrays
            if isinstance(parsed_data, list):
                data = next((item for item in parsed_data if is_recipe(item)), None)
            elif isinstance(parsed_data, dict):
                # Handle @graph structure (multiple items in a graph)
                if '@graph' in parsed_data:
                    graph = parsed_data['@graph']
                    if isinstance(graph, list):
                        data = next((item for item in graph if is_recipe(item)), None)
                elif is_recipe(parsed_data):
                    data = parsed_data
            
            # If we found a recipe, stop searching
            if data:
                break
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"Could not parse JSON-LD: {e}")
            continue
    
    # If we found recipe data in JSON-LD, extract it
    if data:
        # Extract structured recipe data
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
        logger.info(f"Extracted structured recipe data: {len(text)} characters")
        return text
    
    # Fallback: Look for common recipe container elements
    for selector in ['[itemtype*="Recipe"]', '.recipe', '#recipe', 'article']:
        recipe_container = soup.select_one(selector)
        if recipe_container:
            logger.debug(f"Found recipe container: {selector}")
            break
    
    # If we found a recipe container, work with that; otherwise use the whole page
    if recipe_container:
        soup = recipe_container
    
    # Remove unnecessary elements to reduce text size
    for element in soup(["script", "style", "nav", "header", "footer", "aside", 
                         "iframe", "noscript", "svg"]):
        element.extract()
    
    # Remove common non-recipe sections (but be less aggressive if we have a recipe container)
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
    
    # Get text with newline separators to preserve structure better
    text = soup.get_text(separator='\n')
    
    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    # Limit text length to avoid rate limits (keep first ~8000 chars which should contain the recipe)
    if len(text) > 8000:
        logger.warning(f"Text too long ({len(text)} chars), truncating to 8000 chars")
        text = text[:8000]
    
    logger.info(f"Extracted text length: {len(text)} characters")
    return text


def generate_html_visualization(recipe, original_text: str) -> str:
    """Generate an HTML visualization of the parsed recipe.
    
    Args:
        recipe: The parsed Recipe object
        original_text: The original recipe text
        
    Returns:
        HTML content as a string
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{recipe.title} - Parsed Recipe</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        .panel {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        h2 {{
            color: #666;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 5px;
        }}
        .meta {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            font-size: 14px;
            color: #666;
        }}
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .description {{
            font-style: italic;
            color: #666;
            margin-bottom: 20px;
        }}
        .ingredient {{
            display: flex;
            gap: 10px;
            margin-bottom: 8px;
            padding: 8px;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .quantity {{
            font-weight: bold;
            color: #2196F3;
            min-width: 50px;
        }}
        .unit {{
            color: #666;
            min-width: 50px;
        }}
        .name {{
            flex: 1;
        }}
        .instruction {{
            margin-bottom: 15px;
            padding-left: 30px;
            position: relative;
        }}
        .instruction::before {{
            content: counter(step);
            counter-increment: step;
            position: absolute;
            left: 0;
            top: 0;
            background: #2196F3;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
        }}
        .instructions {{
            counter-reset: step;
        }}
        .original-text {{
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.5;
            color: #444;
        }}
        @media (max-width: 768px) {{
            .container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="panel">
            <h1>{recipe.title}</h1>
            
            <h2>Ingredients</h2>
            <div class="ingredients">
"""
    
    # Group ingredients by their group field
    from itertools import groupby
    grouped_ingredients = []
    for group_name, items in groupby(recipe.ingredients, key=lambda x: x.group):
        grouped_ingredients.append((group_name, list(items)))
    
    for group_name, ingredients in grouped_ingredients:
        if group_name:
            html += f"""
                <h3 style="margin-top: 20px; margin-bottom: 10px; color: #2196F3; font-size: 16px;">{group_name}</h3>
"""
        
        for ing in ingredients:
            quantity_str = f"{ing.quantity}" if ing.quantity is not None else ""
            unit_str = ing.unit if ing.unit else ""
            html += f"""
                <div class="ingredient">
                    <span class="quantity">{quantity_str}</span>
                    <span class="unit">{unit_str}</span>
                    <span class="name">{ing.name}</span>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="panel">
            <h2>Original Recipe Text</h2>
            <div class="original-text">{original_text}</div>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def parse_recipe_from_url(url: str, output_dir: Path, api_key: str, model: str) -> bool:
    """Parse a recipe from a URL and save the results.
    
    Args:
        url: URL of the recipe website
        output_dir: Directory to save the output files
        api_key: API key for the language model
        model: The model to use for extraction
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Fetch the recipe text from the URL
        recipe_text = fetch_recipe_text(url)
        
        if not recipe_text.strip():
            logger.error("Failed to extract text from URL")
            return False
        
        # Initialize the extractor
        extractor = RecipeExtractor(api_key=api_key, model=model)
        
        # Extract the recipe
        logger.info("Extracting recipe structure...")
        recipe = extractor.extract_recipe(recipe_text)
        
        if not recipe:
            logger.error("Failed to extract recipe from the text")
            return False
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename based on recipe title
        safe_title = "".join(c for c in recipe.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_').lower()
        if not safe_title:
            safe_title = "recipe"
        
        # Save the JSON output
        json_file = output_dir / f"{safe_title}.json"
        logger.info(f"Saving structured recipe to: {json_file}")
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(recipe.model_dump(), f, indent=2, ensure_ascii=False)
        
        # Create an HTML visualization
        html_file = output_dir / f"{safe_title}.html"
        logger.info(f"Creating HTML visualization: {html_file}")
        
        html_content = generate_html_visualization(recipe, recipe_text)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Print summary
        print(f"\n✅ Recipe successfully parsed!")
        print(f"📝 Title: {recipe.title}")
        print(f"🥘 Ingredients: {len(recipe.ingredients)}")
        print(f"\n📄 Output files:")
        print(f"   - JSON: {json_file}")
        print(f"   - HTML: {html_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error parsing recipe: {str(e)}", exc_info=True)
        return False


def main():
    """Main entry point for the recipe converter."""
    parser = argparse.ArgumentParser(
        description="Extract recipes from websites into structured JSON format"
    )
    parser.add_argument(
        "url",
        type=str,
        help="URL of the recipe website"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory to save output files (default: ./output)"
    )
    parser.add_argument(
        "--api-key",
        help="API key for the language model (can also be set via LANGEXTRACT_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        help="Model to use for extraction (default: gemini-2.5-pro)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv("LANGEXTRACT_API_KEY")
    if not api_key:
        logger.error("API key not provided. Set LANGEXTRACT_API_KEY env var or use --api-key")
        sys.exit(1)
    
    # Parse the recipe
    success = parse_recipe_from_url(
        url=args.url,
        output_dir=args.output_dir,
        api_key=api_key,
        model=args.model
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
