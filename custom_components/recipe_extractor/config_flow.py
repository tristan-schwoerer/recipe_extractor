"""Config flow for Recipe Extractor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    CONF_TODO_ENTITY,
    CONF_DEFAULT_MODEL,
    CONF_API_KEY,
    CONF_CONVERT_UNITS,
)

_LOGGER = logging.getLogger(__name__)


class RecipeExtractorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Recipe Extractor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            # Validate API key
            api_key = user_input.get(CONF_API_KEY, "").strip()
            if not api_key:
                errors[CONF_API_KEY] = "api_key_required"

            # Clean up empty strings to None
            if CONF_TODO_ENTITY in user_input:
                if not user_input[CONF_TODO_ENTITY].strip():
                    user_input[CONF_TODO_ENTITY] = None

            if not errors:
                _LOGGER.info("Creating Recipe Extractor config entry")
                # Create the config entry with options
                return self.async_create_entry(
                    title="Recipe Extractor",
                    data={},
                    options=user_input,
                )

        # Show the configuration form with all options
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Optional(CONF_TODO_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="todo",
                        ),
                    ),
                    vol.Optional(
                        CONF_DEFAULT_MODEL,
                        default=DEFAULT_MODEL,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=AVAILABLE_MODELS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                    vol.Optional(
                        CONF_CONVERT_UNITS,
                        default=True,
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RecipeExtractorOptionsFlow:
        """Get the options flow for this handler."""
        return RecipeExtractorOptionsFlow(config_entry)


class RecipeExtractorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Recipe Extractor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate API key if provided
            api_key = user_input.get(CONF_API_KEY)
            if api_key is not None:
                api_key = api_key.strip()
                if not api_key:
                    errors[CONF_API_KEY] = "api_key_required"
                else:
                    user_input[CONF_API_KEY] = api_key

            # Clean up empty strings to None
            if CONF_TODO_ENTITY in user_input:
                if not user_input.get(CONF_TODO_ENTITY, "").strip():
                    user_input[CONF_TODO_ENTITY] = None

            if not errors:
                _LOGGER.info("Updating Recipe Extractor options")
                return self.async_create_entry(title="", data=user_input)

        # Get current options with proper defaults
        current_api_key = self.config_entry.options.get(CONF_API_KEY, "")
        current_todo_entity = self.config_entry.options.get(CONF_TODO_ENTITY)
        current_model = self.config_entry.options.get(
            CONF_DEFAULT_MODEL, DEFAULT_MODEL)
        current_convert = self.config_entry.options.get(
            CONF_CONVERT_UNITS, True)

        # Build schema with conditional defaults
        schema_dict = {
            vol.Optional(
                CONF_API_KEY,
                default=current_api_key,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                ),
            ),
        }

        # Only add default for todo_entity if it has a value
        if current_todo_entity:
            schema_dict[vol.Optional(CONF_TODO_ENTITY, default=current_todo_entity)] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="todo",
                ),
            )
        else:
            schema_dict[vol.Optional(CONF_TODO_ENTITY)] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="todo",
                ),
            )

        schema_dict.update({
            vol.Optional(
                CONF_DEFAULT_MODEL,
                default=current_model,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=AVAILABLE_MODELS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                ),
            ),
            vol.Optional(
                CONF_CONVERT_UNITS,
                default=current_convert,
            ): selector.BooleanSelector(),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
