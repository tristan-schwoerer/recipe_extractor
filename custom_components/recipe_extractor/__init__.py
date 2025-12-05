"""
Recipe Extractor Integration for Home Assistant.

This integration provides a service to extract structured recipe data from recipe websites using AI-powered extraction.
"""
import asyncio
from typing import Optional

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .unit_converter import convert_to_metric, format_quantity

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_MODEL,
    DEFAULT_MODEL,
    SERVICE_EXTRACT,
    SERVICE_EXTRACT_TO_LIST,
    EVENT_RECIPE_EXTRACTED,
    EVENT_EXTRACTION_FAILED,
    DATA_URL,
    DATA_MODEL,
    DATA_RECIPE,
    DATA_ERROR,
    DATA_TODO_ENTITY,
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

# Service schemas
SERVICE_EXTRACT_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_URL): cv.url,
        vol.Optional(DATA_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)

SERVICE_EXTRACT_TO_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_URL): cv.url,
        vol.Optional(DATA_TODO_ENTITY): cv.entity_id,
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
    # Support for YAML configuration (legacy)
    if DOMAIN in config:
        api_key = config[DOMAIN][CONF_API_KEY]
        default_model = config[DOMAIN].get(CONF_MODEL, DEFAULT_MODEL)
        await _setup_services(hass, api_key, default_model)
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Recipe Extractor from a config entry."""
    # Priority: options > entry data > YAML config
    api_key = entry.options.get("api_key", entry.data.get(CONF_API_KEY, ""))
    default_model = entry.options.get("default_model", entry.data.get(CONF_MODEL, DEFAULT_MODEL))
    
    # If no API key in options/entry, try to get from YAML config
    if not api_key and DOMAIN in hass.data.get("configuration", {}):
        api_key = hass.data["configuration"].get(DOMAIN, {}).get(CONF_API_KEY, "")
    
    await _setup_services(hass, api_key, default_model, entry)
    
    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services when entry is unloaded
    hass.services.async_remove(DOMAIN, SERVICE_EXTRACT)
    hass.services.async_remove(DOMAIN, SERVICE_EXTRACT_TO_LIST)
    
    return True


async def _setup_services(hass: HomeAssistant, api_key: str, default_model: str, entry: ConfigEntry = None) -> None:
    """Set up the integration services."""
    
    def _get_current_api_key() -> str:
        """Get the current API key, checking options first."""
        if entry:
            return entry.options.get("api_key", api_key) or api_key
        return api_key
    
    def _get_current_model() -> str:
        """Get the current model, checking options first."""
        if entry:
            return entry.options.get("default_model", default_model) or default_model
        return default_model
    async def handle_extract_recipe(call: ServiceCall) -> None:
        """Handle the extract recipe service call."""
        url = call.data[DATA_URL]
        model = call.data.get(DATA_MODEL, _get_current_model())
        current_api_key = _get_current_api_key()
        
        try:
            # Run extraction in executor (blocking I/O)
            recipe_data = await hass.async_add_executor_job(
                _extract_recipe_sync, url, current_api_key, model
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
    
    async def handle_extract_to_list(call: ServiceCall) -> None:
        """Handle the extract to list service call."""
        url = call.data[DATA_URL]
        todo_entity = call.data.get(DATA_TODO_ENTITY)
        
        # If no todo entity provided, try to get from options
        if not todo_entity and entry:
            todo_entity = entry.options.get("default_todo_entity")
        
        if not todo_entity:
            error_msg = "No todo entity specified and no default configured"
            hass.bus.async_fire(
                EVENT_EXTRACTION_FAILED,
                {
                    DATA_URL: url,
                    DATA_ERROR: error_msg,
                }
            )
            return
        
        model = call.data.get(DATA_MODEL, _get_current_model())
        current_api_key = _get_current_api_key()
        
        try:
            # Run extraction in executor (blocking I/O)
            recipe_data = await hass.async_add_executor_job(
                _extract_recipe_sync, url, current_api_key, model
            )
            
            if recipe_data:
                # Check if unit conversion is enabled
                convert_units = entry.options.get("convert_to_metric", True) if entry else True
                
                # Prepare all ingredients first
                todo_items = []
                for ingredient in recipe_data.get('ingredients', []):
                    # Format ingredient text, skipping null/empty values
                    parts = []
                    quantity = ingredient.get('quantity')
                    unit = ingredient.get('unit')
                    name = ingredient.get('name')
                    
                    # Clean null strings
                    if quantity == 'null' or quantity == 'None':
                        quantity = None
                    if unit == 'null' or unit == 'None':
                        unit = None
                    if name == 'null' or name == 'None':
                        name = None
                    
                    # Convert units if enabled
                    if convert_units and quantity is not None and unit:
                        try:
                            quantity, unit = convert_to_metric(float(quantity), unit)
                        except (ValueError, TypeError):
                            pass  # Keep original if conversion fails
                    
                    # Add parts only if they have actual values
                    if quantity is not None and str(quantity).strip() and str(quantity) != '':
                        parts.append(format_quantity(quantity))
                    if unit is not None and str(unit).strip() and str(unit) != '':
                        parts.append(str(unit))
                    if name is not None and str(name).strip() and str(name) != '':
                        parts.append(str(name))
                    
                    if parts:  # Only add if there's content
                        todo_items.append(' '.join(parts))
                
                # Add all ingredients concurrently for better performance
                if todo_items:
                    tasks = [
                        hass.services.async_call(
                            'todo',
                            'add_item',
                            {
                                'entity_id': todo_entity,
                                'item': item_text,
                            },
                            blocking=False,
                        )
                        for item_text in todo_items
                    ]
                    await asyncio.gather(*tasks)
                
                # Fire success event
                hass.bus.async_fire(
                    EVENT_RECIPE_EXTRACTED,
                    {
                        DATA_URL: url,
                        DATA_RECIPE: recipe_data,
                        DATA_TODO_ENTITY: todo_entity,
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
    
    # Register the services
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT,
        handle_extract_recipe,
        schema=SERVICE_EXTRACT_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT_TO_LIST,
        handle_extract_to_list,
        schema=SERVICE_EXTRACT_TO_LIST_SCHEMA,
    )
