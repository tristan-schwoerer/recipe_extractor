"""
Service Handlers.

This module contains the Home Assistant service handler functions for
recipe extraction, adding recipes to todo lists, and combined operations.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from types import SimpleNamespace

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from ..const import (
    DOMAIN,
    EVENT_RECIPE_EXTRACTED,
    EVENT_EXTRACTION_FAILED,
    DATA_URL,
    DATA_MODEL,
    DATA_RECIPE,
    DATA_ERROR,
    DATA_TODO_ENTITY,
    DATA_TARGET_SERVINGS,
)
from .recipe_service import extract_recipe
from .ingredient_formatter import scale_ingredients, format_ingredients_for_todo

_LOGGER = logging.getLogger(__name__)


def get_entry_config(hass: HomeAssistant) -> dict[str, Any] | None:
    """Get configuration from the first available config entry.

    Returns:
        Configuration dict or None if no entries exist
    """
    if not hass.data.get(DOMAIN):
        return None

    # Get first entry's config (services are shared across all entries)
    entry_id = next(iter(hass.data[DOMAIN]))
    return hass.data[DOMAIN][entry_id]


async def handle_extract_recipe(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Handle the extract recipe service call.

    Args:
        hass: Home Assistant instance
        call: Service call with url and optional model

    Returns:
        Dictionary with recipe data or error
    """
    url = call.data[DATA_URL]

    # Get configuration
    config = get_entry_config(hass)
    if not config:
        _LOGGER.error("No configuration found for Recipe Extractor")
        raise ServiceValidationError("Recipe Extractor is not configured")

    model = call.data.get(DATA_MODEL, config["default_model"])
    api_key = config["api_key"]

    _LOGGER.info("Extracting recipe from %s using model %s", url, model)

    try:
        # Run extraction in executor (blocking I/O)
        recipe_data = await hass.async_add_executor_job(
            extract_recipe, url, api_key, model
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


async def handle_add_to_list(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Handle the add to list service call.

    Args:
        hass: Home Assistant instance
        call: Service call with recipe data, optional todo_entity and target_servings

    Returns:
        Dictionary with result or error
    """
    recipe_data = call.data[DATA_RECIPE]
    todo_entity = call.data.get(DATA_TODO_ENTITY)
    target_servings = call.data.get(DATA_TARGET_SERVINGS)

    # Get configuration
    config = get_entry_config(hass)
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
            "Adding recipe '%s' ingredients to %s",
            recipe_data.get('title', 'Unknown'),
            todo_entity
        )

        _LOGGER.debug(
            "Recipe data: title='%s', servings=%s, ingredients count=%d",
            recipe_data.get('title'),
            recipe_data.get('servings'),
            len(recipe_data.get('ingredients', []))
        )

        # Log the raw ingredients for debugging
        for idx, ing in enumerate(recipe_data.get('ingredients', [])):
            _LOGGER.debug("Ingredient %d: %s", idx + 1, ing)

        # Scale ingredients if target servings specified
        ingredients = recipe_data.get('ingredients', [])
        if target_servings:
            original_servings = recipe_data.get('servings')
            ingredients = scale_ingredients(
                ingredients, original_servings, target_servings)

        # Prepare all ingredients
        todo_items = format_ingredients_for_todo(ingredients, convert_units)
        _LOGGER.debug("Formatted %d todo items from ingredients",
                      len(todo_items))

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
            _LOGGER.info(
                "Successfully added %d ingredients to %s",
                len(todo_items),
                todo_entity
            )
        else:
            _LOGGER.warning("No ingredients to add - todo_items list is empty")

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


async def handle_extract_to_list(hass: HomeAssistant, call: ServiceCall) -> dict[str, Any]:
    """Handle the extract to list service call.

    This is a convenience service that combines extract_recipe and add_to_list.

    Args:
        hass: Home Assistant instance
        call: Service call with url, optional todo_entity, target_servings, and model

    Returns:
        Dictionary with result or error
    """
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
        extract_call = SimpleNamespace(data=extract_data)
        extract_result = await handle_extract_recipe(hass, extract_call)

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
        add_result = await handle_add_to_list(hass, add_call)

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
        _LOGGER.error(
            "Recipe extraction to list failed for %s: %s",
            url,
            error_msg,
            exc_info=True
        )
        hass.bus.async_fire(
            EVENT_EXTRACTION_FAILED,
            {
                DATA_URL: url,
                DATA_ERROR: error_msg,
            }
        )
        return {"error": error_msg}
