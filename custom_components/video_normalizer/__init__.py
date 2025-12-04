"""The Video Normalizer integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

_LOGGER = logging.getLogger(__name__)

DOMAIN = "video_normalizer"
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Video Normalizer from a config entry."""
    _LOGGER.debug("Setting up Video Normalizer integration")
    
    # Store the download directory from config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "download_dir": entry.data.get("download_dir"),
    }
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Video Normalizer integration")
    
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return True
