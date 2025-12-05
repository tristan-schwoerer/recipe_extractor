"""
Recipe Extractor Integration for Home Assistant.

This integration provides a service to extract structured recipe datarom recipe websites using AI-powered extraction.
"""
import asyncio
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
        recipe_text = fetch_recipe_text(url)
        
        if not recipe_text or len(recipe_text.strip()) < 100:
            return None
        
        extractor = RecipeExtractor(api_key=api_key, model=model)
        recipe = extractor.extract_recipe(recipe_text)
        
        if not recipe:
            return None
        
        return recipe.model_dump()
        
    except Exception as e:
        return None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Recipe Extractor integration."""
    
    if DOMAIN not in config:
        return False
    
    api_key = config[DOMAIN][CONF_API_KEY]
    default_model = config[DOMAIN].get(CONF_MODEL, DEFAULT_MODEL)
    
    async def handle_extract_recipe(call: ServiceCall) -> None:
        """Handle the extract recipe service call."""
        url = call.data[DATA_URL]
        model = call.data.get(DATA_MODEL, default_model)
        
        try:
            # Run extraction in executor (blocking I/O)
            recipe_data = await hass.async_add_executor_job(
                _extract_recipe_sync, url, api_key, model
            )
            
            if recipe_data:
                hass.bus.async_fire(
                    EVENT_RECIPE_EXTRACTED,
                    {
                        DATA_URL: url,
                        DATA_RECIPE: recipe_data,
                    }
                )
            else:
                hass.bus.async_fire(
                    EVENT_EXTRACTION_FAILED,
                    {
                        DATA_URL: url,
                        DATA_ERROR: "Failed to extract recipe from URL",
                    }
                )
                
        except Exception as e:
            error_msg = f"Error extracting recipe: {str(e)}"
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
    
    return True
