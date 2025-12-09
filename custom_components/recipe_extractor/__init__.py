"""
Recipe Extractor Integration for Home Assistant.

This integration provides services to extract structured recipe data from recipe 
websites using either JSON-LD parsing or AI-powered extraction.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_MODEL,
    CONF_DEFAULT_TODO_ENTITY,
    CONF_DEFAULT_MODEL,
    CONF_CONVERT_UNITS,
    DEFAULT_MODEL,
    SERVICE_EXTRACT,
    SERVICE_EXTRACT_TO_LIST,
    SERVICE_ADD_TO_LIST,
    DATA_URL,
    DATA_MODEL,
    DATA_RECIPE,
    DATA_TODO_ENTITY,
    DATA_TARGET_SERVINGS,
)
from .services.service_handlers import (
    handle_extract_recipe,
    handle_add_to_list,
    handle_extract_to_list,
)

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
    default_todo_entity = entry.options.get(CONF_DEFAULT_TODO_ENTITY)
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

    # Listen for options updates
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


async def _setup_services(hass: HomeAssistant) -> None:
    """Set up the integration services."""

    async def _handle_extract_recipe(call: ServiceCall) -> dict[str, Any]:
        """Wrapper for handle_extract_recipe that injects hass."""
        return await handle_extract_recipe(hass, call)

    async def _handle_add_to_list(call: ServiceCall) -> dict[str, Any]:
        """Wrapper for handle_add_to_list that injects hass."""
        return await handle_add_to_list(hass, call)

    async def _handle_extract_to_list(call: ServiceCall) -> dict[str, Any]:
        """Wrapper for handle_extract_to_list that injects hass."""
        return await handle_extract_to_list(hass, call)

    # Register the services with supports_response
    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT,
        _handle_extract_recipe,
        schema=SERVICE_EXTRACT_SCHEMA,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TO_LIST,
        _handle_add_to_list,
        schema=SERVICE_ADD_TO_LIST_SCHEMA,
        supports_response=True,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXTRACT_TO_LIST,
        _handle_extract_to_list,
        schema=SERVICE_EXTRACT_TO_LIST_SCHEMA,
        supports_response=True,
    )
