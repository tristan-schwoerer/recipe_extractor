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
    SERVICE_ADD_TO_LIST,
    EVENT_RECIPE_EXTRACTED,
    EVENT_EXTRACTION_FAILED,
    DATA_URL,
    DATA_MODEL,
    DATA_RECIPE,
    DATA_ERROR,
    DATA_TODO_ENTITY,
    DATA_TARGET_SERVINGS,
)
from .extractors.recipe_extractor import RecipeExtractor
from .extractors.scraper import fetch_recipe_text
from .models.recipe import Recipe, Ingredient
import re

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
        vol.Optional(DATA_TARGET_SERVINGS): cv.positive_int,
    }
)

SERVICE_ADD_TO_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(DATA_RECIPE): dict,
        vol.Optional(DATA_TODO_ENTITY): cv.entity_id,
        vol.Optional(DATA_TARGET_SERVINGS): cv.positive_int,
    }
)


def _parse_jsonld_ingredient(ingredient_text: str) -> Ingredient:
    """Parse a JSON-LD ingredient string into structured Ingredient.

    Args:
        ingredient_text: Raw ingredient string like "1 cup butter, softened"

    Returns:
        Structured Ingredient object
    """
    # Common unit abbreviations and full names (English + German/Danish)
    units = r'(?:cups?|tablespoons?|tbsp?|teaspoons?|tsp?|ounces?|oz|pounds?|lbs?|grams?|g|kilograms?|kg|milliliters?|ml|liters?|l|pinch|dash|clove|piece|slice|tl|el|teelöffel|esslöffel|messerspitze|tsk|spsk|knsp|msk|dl)'

    # Try pattern 1: "quantity unit name" (English format: "1 cup butter")
    pattern1 = rf'^([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)\s*({units})?\s*(.+)$'
    match = re.match(pattern1, ingredient_text.strip(), re.IGNORECASE)

    if match:
        quantity_str, unit, name = match.groups()
        try:
            # Handle fractions
            if '/' in quantity_str:
                parts = quantity_str.split()
                quantity = sum(eval(p) for p in parts)
            else:
                quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                 .replace('⅔', '0.667').replace('¼', '0.25')
                                 .replace('¾', '0.75'))
        except:
            quantity = None

        return Ingredient(
            name=name.strip(),
            quantity=quantity,
            unit=unit.strip() if unit else None
        )
    
    # Try pattern 2: "unit name quantity" (German/Danish format: "TL Korianderpulver 0.5")
    pattern2 = rf'^({units})\s+(.+?)\s+([\d./½⅓⅔¼¾⅛⅜⅝⅞]+(?:\s+[\d./½⅓⅔¼¾⅛⅜⅝⅞]+)?)$'
    match = re.match(pattern2, ingredient_text.strip(), re.IGNORECASE)
    
    if match:
        unit, name, quantity_str = match.groups()
        try:
            # Handle fractions
            if '/' in quantity_str:
                parts = quantity_str.split()
                quantity = sum(eval(p) for p in parts)
            else:
                quantity = float(quantity_str.replace('½', '0.5').replace('⅓', '0.333')
                                 .replace('⅔', '0.667').replace('¼', '0.25')
                                 .replace('¾', '0.75'))
        except:
            quantity = None

        return Ingredient(
            name=name.strip(),
            quantity=quantity,
            unit=unit.strip() if unit else None
        )
    else:
        # No quantity detected, just a name
        return Ingredient(name=ingredient_text.strip(), quantity=None, unit=None)


def _parse_jsonld_recipe(recipe_text: str) -> Recipe:
    """Parse JSON-LD structured recipe text directly without AI.

    Args:
        recipe_text: The structured text from JSON-LD extraction

    Returns:
        Recipe object
    """
    lines = recipe_text.split('\n')
    title = ""
    servings = None
    ingredients = []

    in_ingredients = False

    for line in lines:
        line = line.strip()
        if line.startswith("Recipe: "):
            title = line[8:]  # Remove "Recipe: " prefix
        elif line.startswith("Servings: "):
            servings_text = line[10:]  # Remove "Servings: " prefix
            # Extract number from strings like "48", "Makes 10", "6 servings"
            match = re.search(r'\d+', servings_text)
            if match:
                servings = int(match.group())
        elif line == "Ingredients:":
            in_ingredients = True
        elif in_ingredients and line.startswith("- "):
            ingredient_text = line[2:]  # Remove "- " prefix
            ingredients.append(_parse_jsonld_ingredient(ingredient_text))

    return Recipe(title=title, servings=servings, ingredients=ingredients)


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
        recipe_text, is_jsonld = fetch_recipe_text(url)

        if not recipe_text or len(recipe_text.strip()) < 100:
            _LOGGER.warning("Insufficient text content from %s (length: %d)", url, len(
                recipe_text) if recipe_text else 0)
            return None

        _LOGGER.debug("Fetched %d characters of text from %s (JSON-LD: %s)",
                      len(recipe_text), url, is_jsonld)

        # If JSON-LD data was found, parse it directly without AI
        if is_jsonld:
            _LOGGER.info(
                "Using direct JSON-LD parsing (skipping AI inference)")
            recipe = _parse_jsonld_recipe(recipe_text)
        else:
            # Fallback to AI extraction for unstructured HTML text
            _LOGGER.info("Using AI extraction for unstructured text")
            extractor = RecipeExtractor(api_key=api_key, model=model)
            recipe = extractor.extract_recipe(recipe_text)

        if not recipe:
            _LOGGER.warning(
                "Recipe extraction returned no results for %s", url)
            return None

        _LOGGER.info("Successfully extracted recipe '%s' with %d ingredients from %s",
                     recipe.title, len(recipe.ingredients), url)

        # Include extraction method in response
        result = recipe.model_dump()
        result['extraction_method'] = 'json-ld' if is_jsonld else 'ai'
        result['used_ai'] = not is_jsonld
        return result

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
        hass.services.async_remove(DOMAIN, SERVICE_ADD_TO_LIST)
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


def _scale_ingredients(ingredients: list[dict[str, Any]], original_servings: int | None, target_servings: int) -> list[dict[str, Any]]:
    """Scale ingredient quantities based on servings.

    Args:
        ingredients: List of ingredient dicts with name, quantity, unit
        original_servings: Original number of servings in the recipe
        target_servings: Target number of servings to scale to

    Returns:
        List of scaled ingredient dicts
    """
    if original_servings is None or original_servings <= 0:
        _LOGGER.warning(
            "Cannot scale recipe: original servings not available or invalid")
        return ingredients

    if target_servings <= 0:
        _LOGGER.warning(
            "Cannot scale recipe: target servings must be positive")
        return ingredients

    scaling_factor = target_servings / original_servings
    _LOGGER.info("Scaling ingredients from %d to %d servings (factor: %.2f)",
                 original_servings, target_servings, scaling_factor)

    scaled_ingredients = []
    for ingredient in ingredients:
        scaled_ingredient = ingredient.copy()
        if ingredient.get('quantity') is not None:
            original_qty = ingredient['quantity']
            scaled_qty = original_qty * scaling_factor
            scaled_ingredient['quantity'] = scaled_qty
            _LOGGER.debug("Scaled %s: %.2f -> %.2f",
                          ingredient.get('name'), original_qty, scaled_qty)
        scaled_ingredients.append(scaled_ingredient)

    return scaled_ingredients


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
        if not name or name in ('null', 'None', None):
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
        parts.append(str(name))

        if quantity is not None:
            formatted_qty = format_quantity(quantity)
            if formatted_qty:
                parts.append(formatted_qty)

        if unit:
            parts.append(str(unit))

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

    async def handle_add_to_list(call: ServiceCall) -> dict[str, Any]:
        """Handle the add to list service call."""
        recipe_data = call.data[DATA_RECIPE]
        todo_entity = call.data.get(DATA_TODO_ENTITY)
        target_servings = call.data.get(DATA_TARGET_SERVINGS)

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
            raise ServiceValidationError(error_msg)

        convert_units = config.get("convert_units", True)

        try:
            _LOGGER.info(
                "Adding recipe '%s' ingredients to %s", recipe_data.get('title', 'Unknown'), todo_entity)

            _LOGGER.debug("Recipe data: title='%s', servings=%s, ingredients count=%d",
                          recipe_data.get(
                              'title'), recipe_data.get('servings'),
                          len(recipe_data.get('ingredients', [])))

            # Log the raw ingredients for debugging
            for idx, ing in enumerate(recipe_data.get('ingredients', [])):
                _LOGGER.debug("Ingredient %d: %s", idx + 1, ing)

            # Scale ingredients if target servings specified
            ingredients = recipe_data.get('ingredients', [])
            if target_servings:
                original_servings = recipe_data.get('servings')
                ingredients = _scale_ingredients(
                    ingredients, original_servings, target_servings)

            # Prepare all ingredients
            todo_items = _format_ingredients_for_todo(
                ingredients,
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
                        blocking=False,  # Don't block on each item for better performance
                    )
                    for item_text in todo_items
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                _LOGGER.info("Successfully added %d ingredients to %s", len(
                    todo_items), todo_entity)
            else:
                _LOGGER.warning(
                    "No ingredients to add - todo_items list is empty")

            # Return the result as service response
            return {
                "recipe": recipe_data,
                "todo_entity": todo_entity,
                "items_added": len(todo_items)
            }

        except Exception as e:
            error_msg = f"Error adding recipe to list: {str(e)}"
            _LOGGER.error("Failed to add recipe to list: %s",
                          error_msg, exc_info=True)
            return {"error": error_msg}

    async def handle_extract_to_list(call: ServiceCall) -> dict[str, Any]:
        """Handle the extract to list service call."""
        url = call.data[DATA_URL]
        todo_entity = call.data.get(DATA_TODO_ENTITY)
        target_servings = call.data.get(DATA_TARGET_SERVINGS)
        model = call.data.get(DATA_MODEL)

        try:
            # First, extract the recipe
            _LOGGER.info("Extracting recipe from %s", url)

            # Build service data for extract
            extract_data = {DATA_URL: url}
            if model:
                extract_data[DATA_MODEL] = model

            # Create a mock ServiceCall for extract
            from types import SimpleNamespace
            extract_call = SimpleNamespace(data=extract_data)
            extract_result = await handle_extract_recipe(extract_call)

            # Check if extraction was successful
            if "error" in extract_result:
                return extract_result

            recipe_data = extract_result

            # Then, add the extracted recipe to the list
            _LOGGER.info("Adding extracted recipe to list")

            # Build service data for add_to_list
            add_data = {DATA_RECIPE: recipe_data}
            if todo_entity:
                add_data[DATA_TODO_ENTITY] = todo_entity
            if target_servings:
                add_data[DATA_TARGET_SERVINGS] = target_servings

            # Create a mock ServiceCall for add_to_list
            add_call = SimpleNamespace(data=add_data)
            add_result = await handle_add_to_list(add_call)

            # Fire success event
            if "error" not in add_result:
                hass.bus.async_fire(
                    EVENT_RECIPE_EXTRACTED,
                    {
                        DATA_URL: url,
                        DATA_RECIPE: recipe_data,
                        DATA_TODO_ENTITY: add_result.get("todo_entity"),
                    }
                )

            return add_result

        except Exception as e:
            error_msg = f"Error extracting recipe to list: {str(e)}"
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
        SERVICE_ADD_TO_LIST,
        handle_add_to_list,
        schema=SERVICE_ADD_TO_LIST_SCHEMA,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT_TO_LIST,
        handle_extract_to_list,
        schema=SERVICE_EXTRACT_TO_LIST_SCHEMA,
        supports_response=True,
    )
