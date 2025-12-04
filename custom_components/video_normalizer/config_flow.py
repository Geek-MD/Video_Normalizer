"""Config flow for Video Normalizer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DOWNLOADER_DOMAIN, CONF_DOWNLOAD_DIR

_LOGGER = logging.getLogger(__name__)


async def validate_downloader_integration(hass: HomeAssistant) -> dict[str, Any]:
    """Validate that the Downloader integration is installed and configured."""
    # Check if downloader integration is loaded
    if DOWNLOADER_DOMAIN not in hass.config.components:
        _LOGGER.debug("Downloader integration not found in hass.config.components")
        raise DownloaderNotInstalled("Downloader integration is not installed or configured")
    
    _LOGGER.debug("Downloader integration found in components, attempting to retrieve configuration")
    
    # Try multiple methods to get the downloader configuration
    download_dir = None
    
    # Method 1: Check hass.data[DOWNLOADER_DOMAIN] (YAML-based integration)
    downloader_config = hass.data.get(DOWNLOADER_DOMAIN)
    if downloader_config:
        _LOGGER.debug("Found downloader config in hass.data[%s]: %s", DOWNLOADER_DOMAIN, downloader_config)
        if isinstance(downloader_config, dict):
            download_dir = downloader_config.get("download_dir")
        else:
            _LOGGER.debug("downloader_config is not a dict: %s", type(downloader_config))
    else:
        _LOGGER.debug("No data found in hass.data[%s]", DOWNLOADER_DOMAIN)
    
    # Method 2: Check config entries for Downloader
    if not download_dir:
        _LOGGER.debug("Checking config entries for downloader integration")
        for entry in hass.config_entries.async_entries(DOWNLOADER_DOMAIN):
            _LOGGER.debug("Found downloader config entry: %s", entry.data)
            if "download_dir" in entry.data:
                download_dir = entry.data["download_dir"]
                break
    
    # Method 3: Check if data is stored under a different key structure
    if not download_dir and downloader_config:
        _LOGGER.debug("Attempting to extract download_dir from alternative data structures")
        # Try if it's stored directly as a string
        if isinstance(downloader_config, str):
            download_dir = downloader_config
    
    if not download_dir:
        _LOGGER.error(
            "Downloader integration is loaded but no download_dir found. "
            "Available hass.data keys: %s, Config entries: %s",
            list(hass.data.keys()),
            [entry.domain for entry in hass.config_entries.async_entries()]
        )
        raise DownloaderNotConfigured("Downloader integration is not properly configured")
    
    _LOGGER.info("Successfully retrieved download directory from Downloader: %s", download_dir)
    return {"download_dir": download_dir}


class DownloaderNotInstalled(Exception):
    """Error to indicate Downloader integration is not installed."""


class DownloaderNotConfigured(Exception):
    """Error to indicate Downloader integration is not configured."""


class VideoNormalizerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]  # domain parameter is handled by ConfigFlow metaclass
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
                # If Downloader is installed but not configured properly,
                # offer manual configuration as fallback
                return await self.async_step_manual()
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
    
    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration step when Downloader detection fails."""
        errors: dict[str, str] = {}

        if user_input is not None:
            download_dir = user_input.get(CONF_DOWNLOAD_DIR, "").strip()
            
            if not download_dir:
                errors[CONF_DOWNLOAD_DIR] = "download_dir_required"
            else:
                # Create the config entry with manual configuration
                return self.async_create_entry(
                    title="Video Normalizer",
                    data={
                        CONF_DOWNLOAD_DIR: download_dir,
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DOWNLOAD_DIR): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "downloader_url": "https://www.home-assistant.io/integrations/downloader/"
            },
        )
