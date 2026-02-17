"""Config flow for Video Normalizer integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DOWNLOADER_DOMAIN, CONF_DOWNLOAD_DIR, CONF_TIMEOUT, DEFAULT_TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def detect_downloader_integration(hass: HomeAssistant) -> dict[str, Any] | None:
    """Try to detect the Downloader integration configuration."""
    # Check if downloader integration is loaded
    if DOWNLOADER_DOMAIN not in hass.config.components:
        _LOGGER.debug("Downloader integration not found in hass.config.components")
        return None
    
    _LOGGER.debug("Downloader integration found in components, attempting to retrieve configuration")
    
    # Try multiple methods to get the downloader configuration
    download_dir = None
    
    # Method 1: Check hass.data[DOWNLOADER_DOMAIN] (YAML-based integration)
    downloader_config = hass.data.get(DOWNLOADER_DOMAIN)
    if downloader_config:
        _LOGGER.debug("Found downloader config in hass.data[%s] (type: %s)", DOWNLOADER_DOMAIN, type(downloader_config).__name__)
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
            _LOGGER.debug("Found downloader config entry with keys: %s", list(entry.data.keys()))
            if "download_dir" in entry.data:
                download_dir = entry.data["download_dir"]
                break
    
    # Method 3: Check if data is stored under a different key structure
    if not download_dir and downloader_config:
        _LOGGER.debug("Attempting to extract download_dir from alternative data structures")
        # Some integrations may store the download directory as a string value directly
        # This is uncommon but we check for it as a fallback
        if isinstance(downloader_config, str):
            download_dir = downloader_config
    
    if not download_dir:
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Downloader integration is loaded but no download_dir found. "
                "Available integrations: %s",
                [domain for domain in hass.config.components if "download" in domain.lower()]
            )
        return None
    
    _LOGGER.info("Successfully retrieved download directory from Downloader")
    return {"download_dir": download_dir}


class VideoNormalizerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Video Normalizer."""

    VERSION = 1
    
    # Only allow a single config entry
    # This ensures only one instance of Video Normalizer can be configured
    # as the service and sensor are global to the integration
    SINGLE_CONFIG_ENTRY = True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - verify Downloader is installed."""
        # Check if Downloader is installed (required dependency)
        downloader_info = await detect_downloader_integration(self.hass)
        
        if downloader_info is None:
            # Downloader is not installed - abort configuration
            _LOGGER.error("Downloader integration is required but not installed")
            return self.async_abort(
                reason="downloader_required",
                description_placeholders={
                    "downloader_url": "https://www.home-assistant.io/integrations/downloader/",
                },
            )
        
        # Downloader is installed, proceed to configuration
        _LOGGER.info("Downloader integration detected, proceeding with configuration")
        return await self.async_step_configure()
    
    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            download_dir = user_input.get(CONF_DOWNLOAD_DIR, "").strip()
            timeout = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            
            if not download_dir:
                errors[CONF_DOWNLOAD_DIR] = "download_dir_required"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title="Video Normalizer",
                    data={
                        CONF_DOWNLOAD_DIR: download_dir,
                        CONF_TIMEOUT: timeout,
                    },
                )

        # Get Downloader configuration to pre-fill the field
        # We know Downloader is installed because async_step_user verified it
        downloader_info = await detect_downloader_integration(self.hass)
        default_download_dir = ""
        if downloader_info:
            default_download_dir = downloader_info.get("download_dir", "")
            _LOGGER.info("Pre-filling download directory from Downloader: %s", default_download_dir)

        return self.async_show_form(
            step_id="configure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DOWNLOAD_DIR, default=default_download_dir): str,
                    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                        vol.Coerce(int), vol.Range(min=1)
                    ),
                }
            ),
            errors=errors,
        )
