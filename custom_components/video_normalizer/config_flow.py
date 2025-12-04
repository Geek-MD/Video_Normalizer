"""Config flow for Video Normalizer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DOWNLOADER_DOMAIN, CONF_DOWNLOAD_DIR

_LOGGER = logging.getLogger(__name__)


async def validate_downloader_integration(hass: HomeAssistant) -> dict[str, Any]:
    """Validate that the Downloader integration is installed and configured."""
    # Check if downloader integration is loaded
    if DOWNLOADER_DOMAIN not in hass.config.components:
        raise DownloaderNotInstalled("Downloader integration is not installed or configured")
    
    # Get the downloader configuration
    downloader_config = hass.data.get(DOWNLOADER_DOMAIN)
    if not downloader_config:
        raise DownloaderNotConfigured("Downloader integration is not properly configured")
    
    # Extract the download directory
    download_dir = downloader_config.get("download_dir")
    if not download_dir:
        raise DownloaderNotConfigured("Downloader integration does not have a download directory configured")
    
    return {"download_dir": download_dir}


class DownloaderNotInstalled(Exception):
    """Error to indicate Downloader integration is not installed."""


class DownloaderNotConfigured(Exception):
    """Error to indicate Downloader integration is not configured."""


class VideoNormalizerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Video Normalizer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate that Downloader is installed and get its configuration
                info = await validate_downloader_integration(self.hass)
                
                # Create the config entry
                return self.async_create_entry(
                    title="Video Normalizer",
                    data={
                        CONF_DOWNLOAD_DIR: info["download_dir"],
                    },
                )
            except DownloaderNotInstalled:
                errors["base"] = "downloader_not_installed"
            except DownloaderNotConfigured:
                errors["base"] = "downloader_not_configured"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "downloader_url": "https://www.home-assistant.io/integrations/downloader/"
            },
        )
