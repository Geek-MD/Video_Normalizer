"""Sensor platform for Video Normalizer integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Sensor states
STATE_WORKING = "working"
STATE_IDLE = "idle"

# Job result types
JOB_SUCCESS = "success"
JOB_SKIPPED = "skipped"
JOB_FAILED = "failed"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Video Normalizer sensor."""
    _LOGGER.info("Setting up Video Normalizer sensor")
    
    sensor = VideoNormalizerSensor()
    async_add_entities([sensor], True)
    
    # Store sensor reference for service to update
    hass.data[DOMAIN]["sensor"] = sensor


class VideoNormalizerSensor(SensorEntity):
    """Sensor to track Video Normalizer service status."""

    _attr_has_entity_name = True
    _attr_name = "Status"

    def __init__(self) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{DOMAIN}_status"
        self._attr_native_value = STATE_IDLE
        self._attr_extra_state_attributes: dict[str, str | list[str] | None] = {
            "last_job": None,
            "timestamp": None,
            "processes": [],
        }

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        if self._attr_native_value == STATE_WORKING:
            return "mdi:video-check"
        return "mdi:video-check-outline"

    @callback
    def set_working(self) -> None:
        """Set sensor to working state."""
        self._attr_native_value = STATE_WORKING
        self._attr_extra_state_attributes["timestamp"] = datetime.now().isoformat()
        self._attr_extra_state_attributes["processes"] = []
        self.async_write_ha_state()
        _LOGGER.info("Video Normalizer sensor state: working")

    @callback
    def set_idle(
        self, 
        job_result: str, 
        processes: list[str] | None = None
    ) -> None:
        """Set sensor to idle state with job result.
        
        Args:
            job_result: Result of the job (success, skipped, failed)
            processes: List of processes that were performed
        """
        self._attr_native_value = STATE_IDLE
        self._attr_extra_state_attributes["last_job"] = job_result
        self._attr_extra_state_attributes["timestamp"] = datetime.now().isoformat()
        self._attr_extra_state_attributes["processes"] = processes or []
        self.async_write_ha_state()
        _LOGGER.info(
            "Video Normalizer sensor state: idle (result: %s, processes: %s)",
            job_result, processes
        )

    @callback
    def add_process(self, process_name: str) -> None:
        """Add a process to the current list.
        
        Args:
            process_name: Name of the process being performed
        """
        if "processes" not in self._attr_extra_state_attributes:
            self._attr_extra_state_attributes["processes"] = []
        
        processes = self._attr_extra_state_attributes["processes"]
        if isinstance(processes, list):
            processes.append(process_name)
            self.async_write_ha_state()
            _LOGGER.debug("Added process to sensor: %s", process_name)
