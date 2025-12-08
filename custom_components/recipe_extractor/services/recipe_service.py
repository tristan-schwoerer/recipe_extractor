"""
Recipe Extraction Service.

This module orchestrates the extraction of recipe data from URLs,
deciding whether to use JSON-LD parsing or AI extraction.
"""
from __future__ import annotations

import logging
from typing import Any

from ..scrapers.web_scraper import fetch_recipe_text
from ..parsers.ai_parser import AIRecipeParser
from ..parsers.jsonld_parser import JSONLDRecipeParser

_LOGGER = logging.getLogger(__name__)


def extract_recipe(url: str, api_key: str, model: str, event_callback=None) -> dict[str, Any] | None:
    """Extract recipe from URL using JSON-LD or AI.

    This function orchestrates the extraction process:
    1. Fetches recipe text from URL
    2. Checks if JSON-LD structured data is available
    3. Uses direct parsing for JSON-LD or falls back to AI extraction
    4. Returns recipe data with extraction metadata

    Args:
        url: Recipe website URL
        api_key: API key for the language model (used if AI extraction needed)
        model: Model name to use (used if AI extraction needed)
        event_callback: Optional callback to fire events during extraction

    Returns:
        Dictionary with recipe data and extraction metadata, or None if extraction fails

    Raises:
        Exception: Re-raises exceptions for proper error handling in async context
    """
    _LOGGER.debug(
        "Starting recipe extraction from %s using model %s", url, model)

    try:
        recipe_text, is_jsonld = fetch_recipe_text(
            url, event_callback=event_callback)

        if not recipe_text or len(recipe_text.strip()) < 100:
            _LOGGER.warning(
                "Insufficient text content from %s (length: %d)",
                url,
                len(recipe_text) if recipe_text else 0
            )
            return None

        _LOGGER.debug(
            "Fetched %d characters of text from %s (JSON-LD: %s)",
            len(recipe_text),
            url,
            is_jsonld
        )

        # If JSON-LD data was found, parse it directly without AI
        if is_jsonld:
            _LOGGER.info(
                "Using direct JSON-LD parsing (skipping AI inference)")
            parser = JSONLDRecipeParser()
            recipe = parser.parse_recipe(recipe_text)
        else:
            # Fallback to AI extraction for unstructured HTML text
            _LOGGER.info("Using AI extraction for unstructured text")
            parser = AIRecipeParser(api_key=api_key, model=model)
            recipe = parser.parse_recipe(recipe_text)

        if not recipe:
            _LOGGER.warning(
                "Recipe extraction returned no results for %s", url)
            return None

        _LOGGER.info(
            "Successfully extracted recipe '%s' with %d ingredients from %s",
            recipe.title,
            len(recipe.ingredients),
            url
        )

        # Include extraction method in response
        result = recipe.model_dump()
        result['extraction_method'] = 'json-ld' if is_jsonld else 'ai'
        result['used_ai'] = not is_jsonld
        return result

    except Exception as e:
        _LOGGER.error(
            "Error extracting recipe from %s: %s",
            url,
            str(e),
            exc_info=True
        )
        raise
