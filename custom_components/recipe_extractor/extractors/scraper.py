"""
Web scraper utilities for fetching recipe text from various websites.

This module handles fetching and cleaning recipe text from URLs,
with specialized scrapers for sites with poor HTML structure.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import cloudscraper
import requests
from bs4 import BeautifulSoup

from ..const import DEFAULT_TIMEOUT, DEFAULT_MAX_TEXT_LENGTH, DEFAULT_MAX_RESPONSE_SIZE, DEFAULT_MAX_REDIRECTS

_LOGGER = logging.getLogger(__name__)


def _fetch_with_retry(session: requests.Session, url: str, max_retries: int = 3) -> bytes:
    """Fetch URL with exponential backoff retry logic.

    Args:
        session: Requests session to use
        url: URL to fetch
        max_retries: Maximum number of retry attempts

    Returns:
        Response content as bytes

    Raises:
        requests.exceptions.RequestException: If all retries fail
        ValueError: If response is too large or invalid content type
    """
    for attempt in range(max_retries):
        try:
            _LOGGER.debug("Fetching %s (attempt %d/%d)",
                          url, attempt + 1, max_retries)
            # Use stream=True to check headers before downloading
            response = session.get(
                url,
                timeout=DEFAULT_TIMEOUT,
                allow_redirects=True,
                stream=True
            )
            response.raise_for_status()

            # Validate Content-Type before downloading
            content_type = response.headers.get('content-type', '').lower()
            if not ('text/html' in content_type or 'application/xhtml' in content_type or 'application/xml' in content_type):
                _LOGGER.warning(
                    "Invalid content type for %s: %s", url, content_type)
                raise ValueError(
                    f"Invalid content type: {content_type}. Only HTML/XHTML content is allowed.")

            # Check content length before downloading
            content_length = response.headers.get('content-length')
            if content_length:
                content_length = int(content_length)
                if content_length > DEFAULT_MAX_RESPONSE_SIZE:
                    _LOGGER.warning(
                        "Response too large for %s: %d bytes", url, content_length)
                    raise ValueError(
                        f"Response size ({content_length} bytes) exceeds maximum allowed size ({DEFAULT_MAX_RESPONSE_SIZE} bytes)")

            # Download content with size limit enforcement
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > DEFAULT_MAX_RESPONSE_SIZE:
                    _LOGGER.warning(
                        "Response exceeded size limit while downloading from %s", url)
                    raise ValueError(
                        f"Response size exceeds maximum allowed size ({DEFAULT_MAX_RESPONSE_SIZE} bytes)")

            return content
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403 and attempt < max_retries - 1:
                # Wait with exponential backoff for rate limiting
                wait_time = 2 ** attempt
                _LOGGER.warning(
                    "Got 403 for %s, retrying after %ds", url, wait_time)
                time.sleep(wait_time)
                continue
            raise
        except requests.exceptions.Timeout as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                _LOGGER.warning(
                    "Timeout fetching %s, retrying after %ds", url, wait_time)
                time.sleep(wait_time)
                continue
            raise
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                _LOGGER.warning(
                    "Error fetching %s: %s, retrying after %ds", url, e, wait_time)
                time.sleep(wait_time)
                continue
            raise

    raise requests.exceptions.RequestException(
        f"Failed to fetch {url} after {max_retries} attempts")


def fetch_recipe_text(url: str) -> str:
    """Fetch and clean recipe text from a URL.

    Uses specialized scrapers when available for better structure preservation,
    otherwise falls back to generic text extraction.

    Args:
        url: The URL of the recipe website

    Returns:
        Cleaned recipe text

    Raises:
        requests.exceptions.RequestException: If fetching fails
        ValueError: If URL is invalid or content is insufficient
    """
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")

    _LOGGER.info("Fetching recipe from %s", url)

    # Use cloudscraper for better anti-bot protection
    _LOGGER.debug("Using cloudscraper for %s", url)
    session = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    session.max_redirects = DEFAULT_MAX_REDIRECTS

    try:
        html = _fetch_with_retry(session, url)
        _LOGGER.debug("Successfully fetched %d bytes from %s", len(html), url)
    except requests.exceptions.RequestException as e:
        _LOGGER.error("Failed to fetch %s: %s", url, str(e))
        raise

    soup = BeautifulSoup(html, features="html.parser")

    # Helper function to check if an item is a Recipe
    def is_recipe(item: Any) -> bool:
        """Check if a JSON-LD item represents a Recipe."""
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

    _LOGGER.debug("Found %d JSON-LD scripts in %s", len(json_lds), url)

    for idx, json_ld in enumerate(json_lds):
        try:
            if not json_ld.string:
                continue

            parsed_data = json.loads(json_ld.string)

            if isinstance(parsed_data, list):
                data = next(
                    (item for item in parsed_data if is_recipe(item)), None)
            elif isinstance(parsed_data, dict):
                if '@graph' in parsed_data:
                    graph = parsed_data['@graph']
                    if isinstance(graph, list):
                        data = next(
                            (item for item in graph if is_recipe(item)), None)
                elif is_recipe(parsed_data):
                    data = parsed_data

            if data:
                _LOGGER.debug("Found recipe data in JSON-LD script %d", idx)
                break

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            _LOGGER.debug("Failed to parse JSON-LD script %d: %s", idx, e)
            continue

    # If we found recipe data in JSON-LD, extract it
    if data:
        parts = []
        if data.get('name'):
            parts.append(f"Recipe: {data['name']}")
        if data.get('recipeYield'):
            # Extract servings/yield information
            recipe_yield = data['recipeYield']
            if isinstance(recipe_yield, list):
                recipe_yield = recipe_yield[0] if recipe_yield else None
            if recipe_yield:
                parts.append(f"\nServings: {recipe_yield}")
        if data.get('recipeIngredient'):
            parts.append("\nIngredients:")
            for ingredient in data['recipeIngredient']:
                parts.append(f"- {ingredient}")
        # NOTE: Instructions are intentionally excluded to prevent duplicate ingredient extraction.
        # LangExtract can extract ingredient patterns from instructions (e.g., "add 250g flour"),
        # which creates duplicate entries when ingredients are mentioned in cooking steps.
        # We only need title, servings, and ingredients for proper extraction.

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

    original_length = len(text)

    # Limit text length to avoid rate limits and improve extraction quality
    if len(text) > DEFAULT_MAX_TEXT_LENGTH:
        _LOGGER.debug("Truncating text from %d to %d characters",
                      original_length, DEFAULT_MAX_TEXT_LENGTH)
        text = text[:DEFAULT_MAX_TEXT_LENGTH]

    _LOGGER.info("Extracted %d characters of text from %s", len(text), url)
    return text
