"""
Recipe Extractor Integration for Home Assistant.

This integration provides a service to extract structured recipe data
from recipe websites using AI-powered extraction.
"""
import asyncio
import logging
from typing import Optional

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_MODEL,
    DEFAULT_MODEL,
    SERVICE_EXTRACT,
    EVENT_RECIPE_EXTRACTED,
    EVENT_EXTRACTION_FAILED,
    DATA_URL,
    DATA_MODEL,
    DATA_RECIPE,
    DATA_ERROR,
)
from .extractors.recipe_extractor import RecipeExtractor
from .extractors.scraper import fetch_recipe_text

_LOGGER = logging.getLogger(__name__)

# Configuration schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schema
SERVICE_EXTRACT_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_URL): cv.url,
        vol.Optional(DATA_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)


def _extract_recipe_sync(url: str, api_key: str, model: str) -> Optional[dict]:
    """Synchronous recipe extraction (runs in executor).
    
    Args:
        url: Recipe website URL
        api_key: API key for the language model
        model: Model name to use
        
    Returns:
        Dictionary with recipe data or None if extraction fails
    """
    try:
        # Fetch recipe text
        _LOGGER.info(f"Fetching recipe from URL: {url}")
        recipe_text = fetch_recipe_text(url)
        
        if not recipe_text or len(recipe_text.strip()) < 100:
            _LOGGER.error("Failed to extract sufficient text from URL")
            return None
        
        # Extract structured recipe
        _LOGGER.info(f"Extracting recipe structure using model: {model}")
        extractor = RecipeExtractor(api_key=api_key, model=model)
        recipe = extractor.extract_recipe(recipe_text)
        
        if not recipe:
            _LOGGER.error("Failed to extract recipe structure")
            return None
        
        _LOGGER.info(f"Successfully extracted recipe: {recipe.title} ({len(recipe.ingredients)} ingredients)")
        return recipe.model_dump()
        
    except Exception as e:
        _LOGGER.error(f"Error during recipe extraction: {str(e)}", exc_info=True)
        return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Recipe Extractor integration."""
    
    if DOMAIN not in config:
        _LOGGER.error(
            "Recipe Extractor integration requires configuration. "
            "Add 'recipe_extractor:' section to configuration.yaml with 'api_key' parameter."
        )
        return False
    
    api_key = config[DOMAIN][CONF_API_KEY]
    default_model = config[DOMAIN].get(CONF_MODEL, DEFAULT_MODEL)
    
    _LOGGER.info(f"Setting up Recipe Extractor integration with model: {default_model}")
    
    async def handle_extract_recipe(call: ServiceCall) -> None:
        """Handle the extract recipe service call."""
        url = call.data[DATA_URL]
        model = call.data.get(DATA_MODEL, default_model)
        
        _LOGGER.info(f"Recipe extraction service called for URL: {url}")
        
        try:
            # Run extraction in executor (blocking I/O)
            recipe_data = await hass.async_add_executor_job(
                _extract_recipe_sync, url, api_key, model
            )
            
            if recipe_data:
                # Fire success event with recipe data
                hass.bus.async_fire(
                    EVENT_RECIPE_EXTRACTED,
                    {
                        DATA_URL: url,
                        DATA_RECIPE: recipe_data,
                    }
                )
                _LOGGER.info(f"Recipe extraction completed: {recipe_data.get('title')}")
            else:
                # Fire failure event
                hass.bus.async_fire(
                    EVENT_EXTRACTION_FAILED,
                    {
                        DATA_URL: url,
                        DATA_ERROR: "Failed to extract recipe from URL",
                    }
                )
                _LOGGER.error(f"Recipe extraction failed for URL: {url}")
                
        except Exception as e:
            error_msg = f"Error extracting recipe: {str(e)}"
            _LOGGER.error(error_msg, exc_info=True)
            hass.bus.async_fire(
                EVENT_EXTRACTION_FAILED,
                {
                    DATA_URL: url,
                    DATA_ERROR: error_msg,
                }
            )
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT,
        handle_extract_recipe,
        schema=SERVICE_EXTRACT_SCHEMA,
    )
    
    _LOGGER.info("Recipe Extractor integration setup complete")
    return True
