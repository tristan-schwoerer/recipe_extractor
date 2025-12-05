"""Config flow for Recipe Extractor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RecipeExtractorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Recipe Extractor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Create the config entry
            return self.async_create_entry(
                title="Recipe Extractor",
                data={},
            )

        # Show the configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "description": "This integration allows you to extract recipes from URLs using AI."
            },
        )
