"""Config flow for Recipe Extractor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DOMAIN, AVAILABLE_MODELS, DEFAULT_MODEL, CONF_TODO_ENTITY, CONF_DEFAULT_MODEL, CONF_API_KEY_OPTION, CONF_CONVERT_UNITS

_LOGGER = logging.getLogger(__name__)


class RecipeExtractorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Recipe Extractor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        
        if user_input is not None:
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
                    vol.Optional(
                        CONF_API_KEY_OPTION,
                        default="",
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Optional(
                        CONF_TODO_ENTITY,
                        default="",
                    ): selector.EntitySelector(
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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_API_KEY_OPTION,
                        default=self.config_entry.options.get(CONF_API_KEY_OPTION, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Optional(
                        CONF_TODO_ENTITY,
                        default=self.config_entry.options.get(CONF_TODO_ENTITY, ""),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="todo",
                        ),
                    ),
                    vol.Optional(
                        CONF_DEFAULT_MODEL,
                        default=self.config_entry.options.get(CONF_DEFAULT_MODEL, DEFAULT_MODEL),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=AVAILABLE_MODELS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        ),
                    ),
                    vol.Optional(
                        CONF_CONVERT_UNITS,
                        default=self.config_entry.options.get(CONF_CONVERT_UNITS, True),
                    ): selector.BooleanSelector(),
                }
            ),
        )
