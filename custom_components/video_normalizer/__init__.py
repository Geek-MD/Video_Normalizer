"""The Video Normalizer integration."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import SupportsResponse

from .const import CONF_TIMEOUT, DEFAULT_TIMEOUT
from .video_processor import VideoProcessor

_LOGGER = logging.getLogger(__name__)

DOMAIN = "video_normalizer"
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Service constants
SERVICE_NORMALIZE_VIDEO = "normalize_video"


async def _ensure_event_processed() -> None:
    """Yield to event loop to ensure events are processed.
    
    This is called after hass.bus.async_fire() to ensure the event
    is processed by the event loop before the service continues.
    This prevents race conditions where the service completes before
    automations can catch the fired events.
    """
    await asyncio.sleep(0)


# Service schema
SERVICE_NORMALIZE_VIDEO_SCHEMA = vol.Schema(
    {
        vol.Required("input_file_path"): cv.string,
        vol.Optional("output_file_path"): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
        vol.Optional("normalize_aspect", default=True): cv.boolean,
        vol.Optional("generate_thumbnail", default=True): cv.boolean,
        vol.Optional("resize_width"): cv.positive_int,
        vol.Optional("resize_height"): cv.positive_int,
        vol.Optional("target_aspect_ratio"): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
        vol.Optional("timeout"): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Video Normalizer from a config entry."""
    _LOGGER.info("Setting up Video Normalizer integration")
    
    # Store the download directory and timeout from config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "download_dir": entry.data.get("download_dir"),
        "timeout": entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
    }
    
    # Initialize video processor
    video_processor = VideoProcessor()
    hass.data[DOMAIN]["processor"] = video_processor
    
    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    async def handle_normalize_video(call: ServiceCall) -> dict[str, Any] | None:
        """Handle the normalize_video service call.
        
        Returns:
            Service response data if call.return_response is True, otherwise None
        """
        input_file_path = call.data["input_file_path"]
        output_file_path = call.data.get("output_file_path")
        overwrite = call.data.get("overwrite", False)
        normalize_aspect = call.data.get("normalize_aspect", True)
        generate_thumbnail = call.data.get("generate_thumbnail", True)
        resize_width = call.data.get("resize_width")
        resize_height = call.data.get("resize_height")
        target_aspect_ratio = call.data.get("target_aspect_ratio")
        
        # Get timeout from service call or use configured default
        timeout = call.data.get("timeout")
        if timeout is None:
            # Use the configured timeout from the entry
            timeout = DEFAULT_TIMEOUT
            for entry_id, entry_data in hass.data[DOMAIN].items():
                if isinstance(entry_data, dict) and CONF_TIMEOUT in entry_data:
                    timeout = entry_data[CONF_TIMEOUT]
                    break
        
        _LOGGER.info("Processing video: %s (timeout: %d seconds)", input_file_path, timeout)
        
        # Track start time for performance logging
        start_time = time.time()
        
        # Get sensor reference
        sensor = hass.data[DOMAIN].get("sensor")
        
        # Set sensor to working state
        if sensor:
            sensor.set_working()
        
        # Track processes performed
        processes_performed: list[str] = []
        
        # Validate video file exists
        if not os.path.exists(input_file_path):
            elapsed_time = time.time() - start_time
            _LOGGER.error(
                "Video file not found: %s - Elapsed time: %.2f seconds - Result: failed (file not found)",
                input_file_path,
                elapsed_time,
            )
            # Fire event before sensor update and cleanup
            hass.bus.async_fire(
                f"{DOMAIN}_video_processing_failed",
                {
                    "video_path": input_file_path,
                    "error": "Video file not found",
                },
            )
            await _ensure_event_processed()
            # Update sensor state to idle after event
            if sensor:
                sensor.set_idle("failed", processes_performed)
            return {"success": False, "error": "Video file not found"} if call.return_response else None
        
        # Parse output_file_path to extract output_path and output_name
        # When overwrite is True, output_file_path is ignored and we use input path
        if overwrite:
            output_path = None
            output_name = None
        elif output_file_path:
            # Split the full path into directory and filename
            output_path = os.path.dirname(output_file_path)
            output_name = os.path.basename(output_file_path)
        else:
            # No output specified and not overwriting
            # This will cause the video processor to use the same directory/name as input
            # which effectively creates a copy with the same name in the same location
            output_path = None
            output_name = None
        
        # Process the video with timeout
        try:
            result = await asyncio.wait_for(
                video_processor.process_video(
                    video_path=input_file_path,
                    output_path=output_path,
                    output_name=output_name,
                    overwrite=overwrite,
                    normalize_aspect=normalize_aspect,
                    generate_thumbnail=generate_thumbnail,
                    resize_width=resize_width,
                    resize_height=resize_height,
                    target_aspect_ratio=target_aspect_ratio,
                ),
                timeout=timeout,
            )
            
            # Collect processes performed
            if result.get("operations"):
                for operation, success in result["operations"].items():
                    if success:
                        processes_performed.append(operation)
            
            # Get temp files for cleanup after event firing and sensor update
            temp_files = result.get("temp_files", [])
            
            if result["success"]:
                # Check if video was skipped (no processing needed)
                if result.get("skipped", False):
                    elapsed_time = time.time() - start_time
                    _LOGGER.info(
                        "Video processing skipped (no changes needed): %s - "
                        "Elapsed time: %.2f seconds - Result: skipped",
                        input_file_path,
                        elapsed_time,
                    )
                    # Fire event before sensor update and cleanup
                    hass.bus.async_fire(
                        f"{DOMAIN}_video_skipped",
                        result,
                    )
                    await _ensure_event_processed()
                    # Update sensor state to idle after event, before cleanup
                    if sensor:
                        sensor.set_idle("skipped", processes_performed)
                else:
                    elapsed_time = time.time() - start_time
                    _LOGGER.info(
                        "Video processed successfully: %s - "
                        "Elapsed time: %.2f seconds - Result: success",
                        input_file_path,
                        elapsed_time,
                    )
                    # Fire event before sensor update and cleanup
                    hass.bus.async_fire(
                        f"{DOMAIN}_video_processing_success",
                        result,
                    )
                    await _ensure_event_processed()
                    # Update sensor state to idle after event, before cleanup
                    if sensor:
                        sensor.set_idle("success", processes_performed)
            else:
                elapsed_time = time.time() - start_time
                _LOGGER.error(
                    "Video processing failed: %s - %s - "
                    "Elapsed time: %.2f seconds - Result: failed",
                    input_file_path,
                    result.get("error", "Unknown error"),
                    elapsed_time,
                )
                # Fire event before sensor update and cleanup
                hass.bus.async_fire(
                    f"{DOMAIN}_video_processing_failed",
                    result,
                )
                await _ensure_event_processed()
                # Update sensor state to idle after event, before cleanup
                if sensor:
                    sensor.set_idle("failed", processes_performed)
            
            # Clean up temporary files AFTER event firing and sensor state update
            # This ensures proper service lifecycle: process → fire events → update sensor → cleanup
            if temp_files:
                video_processor.cleanup_temp_files(temp_files)
            
            # Return response data if requested
            if call.return_response:
                return {
                    "success": result["success"],
                    "skipped": result.get("skipped", False),
                    "output_path": result.get("output_path"),
                    "operations": result.get("operations", {}),
                }
            return None
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            _LOGGER.error(
                "Video processing timed out after %d seconds: %s - "
                "Elapsed time: %.2f seconds - Result: failed (timeout)",
                timeout,
                input_file_path,
                elapsed_time,
            )
            # Fire event before sensor update and cleanup
            hass.bus.async_fire(
                f"{DOMAIN}_video_processing_failed",
                {
                    "video_path": input_file_path,
                    "error": f"Processing timed out after {timeout} seconds",
                },
            )
            await _ensure_event_processed()
            # Update sensor state to idle after event, before cleanup
            if sensor:
                sensor.set_idle("failed", processes_performed)
            # Clean up any temp files that may have been created before timeout
            # This happens AFTER event firing and sensor state update
            video_processor.cleanup_temp_files_by_video_path(input_file_path)
            return {"success": False, "error": f"Processing timed out after {timeout} seconds"} if call.return_response else None
        except Exception as err:
            elapsed_time = time.time() - start_time
            _LOGGER.exception(
                "Unexpected error processing video: %s - "
                "Elapsed time: %.2f seconds - Result: failed (exception)",
                input_file_path,
                elapsed_time,
            )
            # Fire event before sensor update and cleanup
            hass.bus.async_fire(
                f"{DOMAIN}_video_processing_failed",
                {
                    "video_path": input_file_path,
                    "error": str(err),
                },
            )
            await _ensure_event_processed()
            # Update sensor state to idle after event, before cleanup
            if sensor:
                sensor.set_idle("failed", processes_performed)
            # Clean up any temp files that may have been created before exception
            # This happens AFTER event firing and sensor state update
            video_processor.cleanup_temp_files_by_video_path(input_file_path)
            return {"success": False, "error": str(err)} if call.return_response else None
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_NORMALIZE_VIDEO,
        handle_normalize_video,
        schema=SERVICE_NORMALIZE_VIDEO_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    _LOGGER.info("Video Normalizer service registered successfully")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Video Normalizer integration")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if not unload_ok:
        return False
    
    # Unregister the service
    hass.services.async_remove(DOMAIN, SERVICE_NORMALIZE_VIDEO)
    
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove processor and sensor if it's the last entry
        if not any(
            key for key in hass.data[DOMAIN].keys() if key != "processor" and key != "sensor"
        ):
            hass.data[DOMAIN].pop("processor", None)
            hass.data[DOMAIN].pop("sensor", None)
    
    return True
