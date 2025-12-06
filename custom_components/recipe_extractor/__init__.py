"""
Recipe Extractor Integration for Home Assistant.

This integration provides a service to extract structured recipe data from recipe websites using AI-powered extraction.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .unit_converter import convert_to_metric, format_quantity
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_MODEL,
    CONF_TODO_ENTITY,
    CONF_DEFAULT_MODEL,
    CONF_CONVERT_UNITS,
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

_LOGGER = logging.getLogger(__name__)

# Config flow only - no YAML support
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

# Service schemas
SERVICE_EXTRACT_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_URL): cv.url,
        vol.Optional(DATA_MODEL): cv.string,
    }
)

SERVICE_EXTRACT_TO_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_URL): cv.url,
        vol.Optional(DATA_TODO_ENTITY): cv.entity_id,
        vol.Optional(DATA_MODEL): cv.string,
    }
)


def _extract_recipe_sync(url: str, api_key: str, model: str) -> dict | None:
    """Synchronous recipe extraction (runs in executor).

    Args:
        url: Recipe website URL
        api_key: API key for the language model
        model: Model name to use

    Returns:
        Dictionary with recipe data or None if extraction fails

    Raises:
        Exception: Re-raises exceptions for proper error handling in async context
    """
    _LOGGER.debug(
        "Starting recipe extraction from %s using model %s", url, model)

    try:
        recipe_text = fetch_recipe_text(url)

        if not recipe_text or len(recipe_text.strip()) < 100:
            _LOGGER.warning("Insufficient text content from %s (length: %d)", url, len(
                recipe_text) if recipe_text else 0)
            return None

        _LOGGER.debug("Fetched %d characters of text from %s",
                      len(recipe_text), url)

        extractor = RecipeExtractor(api_key=api_key, model=model)
        recipe = extractor.extract_recipe(recipe_text)

        if not recipe:
            _LOGGER.warning(
                "Recipe extraction returned no results for %s", url)
            return None

        _LOGGER.info("Successfully extracted recipe '%s' with %d ingredients from %s",
                     recipe.title, len(recipe.ingredients), url)
        return recipe.model_dump()

    except Exception as e:
        _LOGGER.error("Error extracting recipe from %s: %s",
                      url, str(e), exc_info=True)
        raise


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Recipe Extractor integration."""
    # Initialize integration data storage
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Recipe Extractor integration setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Recipe Extractor from a config entry."""
    _LOGGER.info("Setting up Recipe Extractor config entry")

    # Get configuration from options (preferred) or data
    api_key = entry.options.get(
        CONF_API_KEY) or entry.data.get(CONF_API_KEY, "")
    default_model = entry.options.get(
        CONF_DEFAULT_MODEL) or entry.data.get(CONF_MODEL, DEFAULT_MODEL)
    default_todo_entity = entry.options.get(CONF_TODO_ENTITY)
    convert_units = entry.options.get(CONF_CONVERT_UNITS, True)

    if not api_key:
        _LOGGER.error("No API key configured for Recipe Extractor")
        raise HomeAssistantError("Recipe Extractor requires an API key")

    # Store entry configuration in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "api_key": api_key,
        "default_model": default_model,
        "default_todo_entity": default_todo_entity,
        "convert_units": convert_units,
    }

    # Set up services only once (for the first entry)
    if len(hass.data[DOMAIN]) == 1:
        await _setup_services(hass)
        _LOGGER.info("Recipe Extractor services registered")

        # The card MUST be manually copied to /config/www/ directory by the user
        # Custom integrations cannot automatically serve to /local/ path
        _LOGGER.info(
            "Recipe Extractor card is available in the integration's www/ folder"
        )
        _LOGGER.info(
            "To use the card, copy www/recipe-extractor-card.js to your /config/www/ directory"
        )
        _LOGGER.info(
            "Then add /local/recipe-extractor-card.js as a Lovelace resource"
        )    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.debug("Recipe Extractor config entry setup complete")
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Recipe Extractor config entry")

    # Remove entry data
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # Remove services only if this is the last entry
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_EXTRACT)
        hass.services.async_remove(DOMAIN, SERVICE_EXTRACT_TO_LIST)
        _LOGGER.info("Recipe Extractor services unregistered")

    return True


def _get_entry_config(hass: HomeAssistant) -> dict[str, Any] | None:
    """Get configuration from the first available config entry.

    Returns:
        Configuration dict or None if no entries exist
    """
    if not hass.data.get(DOMAIN):
        return None

    # Get first entry's config (services are shared across all entries)
    entry_id = next(iter(hass.data[DOMAIN]))
    return hass.data[DOMAIN][entry_id]


def _format_ingredients_for_todo(ingredients: list[dict[str, Any]], convert_units: bool) -> list[str]:
    """Format ingredients as strings for todo list.

    Args:
        ingredients: List of ingredient dicts with name, quantity, unit
        convert_units: Whether to convert imperial units to metric

    Returns:
        List of formatted ingredient strings
    """
    todo_items = []

    for idx, ingredient in enumerate(ingredients):
        parts = []
        quantity = ingredient.get('quantity')
        unit = ingredient.get('unit')
        name = ingredient.get('name')

        _LOGGER.debug("Formatting ingredient %d: name='%s', quantity='%s', unit='%s'",
                      idx + 1, name, quantity, unit)

        # Skip invalid values
        if not name or name in ('null', 'None'):
            _LOGGER.debug(
                "Skipping ingredient %d: invalid or missing name", idx + 1)
            continue

        # Clean null-like values
        if quantity in ('null', 'None', None):
            quantity = None
        if unit in ('null', 'None', None):
            unit = None

        # Convert units if enabled
        if convert_units and quantity is not None and unit:
            try:
                original_qty = quantity
                original_unit = unit
                quantity, unit = convert_to_metric(float(quantity), unit)
                _LOGGER.debug("Converted units for %s: %s %s -> %s %s",
                              name, original_qty, original_unit, quantity, unit)
            except (ValueError, TypeError) as e:
                _LOGGER.debug("Failed to convert units for %s: %s", name, e)
                # Keep original if conversion fails

        # Build ingredient string
        if quantity is not None:
            formatted_qty = format_quantity(quantity)
            if formatted_qty:
                parts.append(formatted_qty)

        if unit:
            parts.append(str(unit))

        parts.append(str(name))

        formatted_item = ' '.join(parts)
        _LOGGER.debug("Formatted ingredient %d as: '%s'",
                      idx + 1, formatted_item)
        todo_items.append(formatted_item)

    return todo_items


async def _setup_services(hass: HomeAssistant) -> None:
    """Set up the integration services."""

    async def handle_extract_recipe(call: ServiceCall) -> dict[str, Any]:
        """Handle the extract recipe service call."""
        url = call.data[DATA_URL]

        # Get configuration
        config = _get_entry_config(hass)
        if not config:
            _LOGGER.error("No configuration found for Recipe Extractor")
            raise ServiceValidationError("Recipe Extractor is not configured")

        model = call.data.get(DATA_MODEL, config["default_model"])
        api_key = config["api_key"]

        _LOGGER.info("Extracting recipe from %s using model %s", url, model)

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
                _LOGGER.info("Recipe extraction successful for %s", url)
                # Return the recipe data as service response
                return recipe_data
            else:
                error_msg = "Failed to extract recipe from URL - insufficient content or extraction returned no results"
                _LOGGER.warning("%s: %s", error_msg, url)
                hass.bus.async_fire(
                    EVENT_EXTRACTION_FAILED,
                    {
                        DATA_URL: url,
                        DATA_ERROR: error_msg,
                    }
                )
                return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error extracting recipe: {str(e)}"
            _LOGGER.error("Recipe extraction failed for %s: %s",
                          url, error_msg, exc_info=True)
            hass.bus.async_fire(
                EVENT_EXTRACTION_FAILED,
                {
                    DATA_URL: url,
                    DATA_ERROR: error_msg,
                }
            )
            return {"error": error_msg}

    async def handle_extract_to_list(call: ServiceCall) -> dict[str, Any]:
        """Handle the extract to list service call."""
        url = call.data[DATA_URL]
        todo_entity = call.data.get(DATA_TODO_ENTITY)

        # Get configuration
        config = _get_entry_config(hass)
        if not config:
            _LOGGER.error("No configuration found for Recipe Extractor")
            raise ServiceValidationError("Recipe Extractor is not configured")

        # If no todo entity provided, use default from config
        if not todo_entity:
            todo_entity = config["default_todo_entity"]

        if not todo_entity:
            error_msg = "No todo entity specified and no default configured"
            _LOGGER.error(error_msg)
            hass.bus.async_fire(
                EVENT_EXTRACTION_FAILED,
                {
                    DATA_URL: url,
                    DATA_ERROR: error_msg,
                }
            )
            raise ServiceValidationError(error_msg)

        model = call.data.get(DATA_MODEL, config["default_model"])
        api_key = config["api_key"]
        convert_units = config.get("convert_units", True)

        _LOGGER.info(
            "Extracting recipe from %s to add to %s using model %s", url, todo_entity, model)

        try:
            # Run extraction in executor (blocking I/O)
            recipe_data = await hass.async_add_executor_job(
                _extract_recipe_sync, url, api_key, model
            )

            if recipe_data:
                _LOGGER.debug("Recipe data extracted: title='%s', ingredients count=%d",
                              recipe_data.get('title'), len(recipe_data.get('ingredients', [])))

                # Log the raw ingredients for debugging
                for idx, ing in enumerate(recipe_data.get('ingredients', [])):
                    _LOGGER.debug("Ingredient %d: %s", idx + 1, ing)

                # Prepare all ingredients
                todo_items = _format_ingredients_for_todo(
                    recipe_data.get('ingredients', []),
                    convert_units
                )
                _LOGGER.debug(
                    "Formatted %d todo items from ingredients", len(todo_items))

                # Add all ingredients concurrently for better performance
                if todo_items:
                    _LOGGER.debug("Adding %d ingredients to %s",
                                  len(todo_items), todo_entity)
                    tasks = [
                        hass.services.async_call(
                            'todo',
                            'add_item',
                            {
                                'entity_id': todo_entity,
                                'item': item_text,
                            },
                            blocking=True,
                        )
                        for item_text in todo_items
                    ]
                    await asyncio.gather(*tasks)
                    _LOGGER.info("Successfully added %d ingredients to %s", len(
                        todo_items), todo_entity)
                else:
                    _LOGGER.warning(
                        "No ingredients to add - todo_items list is empty")

                # Fire success event
                hass.bus.async_fire(
                    EVENT_RECIPE_EXTRACTED,
                    {
                        DATA_URL: url,
                        DATA_RECIPE: recipe_data,
                        DATA_TODO_ENTITY: todo_entity,
                    }
                )
                # Return the recipe data as service response
                return {
                    "recipe": recipe_data,
                    "todo_entity": todo_entity,
                    "items_added": len(todo_items)
                }
            else:
                error_msg = "Failed to extract recipe from URL - insufficient content or extraction returned no results"
                _LOGGER.warning("%s: %s", error_msg, url)
                hass.bus.async_fire(
                    EVENT_EXTRACTION_FAILED,
                    {
                        DATA_URL: url,
                        DATA_ERROR: error_msg,
                    }
                )
                return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error extracting recipe: {str(e)}"
            _LOGGER.error("Recipe extraction to list failed for %s: %s",
                          url, error_msg, exc_info=True)
            hass.bus.async_fire(
                EVENT_EXTRACTION_FAILED,
                {
                    DATA_URL: url,
                    DATA_ERROR: error_msg,
                }
            )
            return {"error": error_msg}

    # Register the services with supports_response
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT,
        handle_extract_recipe,
        schema=SERVICE_EXTRACT_SCHEMA,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT_TO_LIST,
        handle_extract_to_list,
        schema=SERVICE_EXTRACT_TO_LIST_SCHEMA,
        supports_response=True,
    )
