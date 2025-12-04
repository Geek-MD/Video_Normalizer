"""The Video Normalizer integration."""
from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .video_processor import VideoProcessor

_LOGGER = logging.getLogger(__name__)

DOMAIN = "video_normalizer"
PLATFORMS: list[Platform] = []

# Service constants
SERVICE_NORMALIZE_VIDEO = "normalize_video"

# Service schema
SERVICE_NORMALIZE_VIDEO_SCHEMA = vol.Schema(
    {
        vol.Required("video_path"): cv.string,
        vol.Optional("output_path"): cv.string,
        vol.Optional("output_name"): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
        vol.Optional("normalize_aspect", default=True): cv.boolean,
        vol.Optional("generate_thumbnail", default=True): cv.boolean,
        vol.Optional("resize_width"): cv.positive_int,
        vol.Optional("resize_height"): cv.positive_int,
        vol.Optional("target_aspect_ratio"): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Video Normalizer from a config entry."""
    _LOGGER.debug("Setting up Video Normalizer integration")
    
    # Store the download directory from config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "download_dir": entry.data.get("download_dir"),
    }
    
    # Initialize video processor
    video_processor = VideoProcessor()
    hass.data[DOMAIN]["processor"] = video_processor
    
    async def handle_normalize_video(call: ServiceCall) -> None:
        """Handle the normalize_video service call."""
        video_path = call.data["video_path"]
        output_path = call.data.get("output_path")
        output_name = call.data.get("output_name")
        overwrite = call.data.get("overwrite", False)
        normalize_aspect = call.data.get("normalize_aspect", True)
        generate_thumbnail = call.data.get("generate_thumbnail", True)
        resize_width = call.data.get("resize_width")
        resize_height = call.data.get("resize_height")
        target_aspect_ratio = call.data.get("target_aspect_ratio")
        
        _LOGGER.info("Processing video: %s", video_path)
        
        # Validate video file exists
        if not os.path.exists(video_path):
            _LOGGER.error("Video file not found: %s", video_path)
            hass.bus.async_fire(
                f"{DOMAIN}_video_processing_failed",
                {
                    "video_path": video_path,
                    "error": "Video file not found",
                },
            )
            return
        
        # Process the video
        try:
            result = await video_processor.process_video(
                video_path=video_path,
                output_path=output_path,
                output_name=output_name,
                overwrite=overwrite,
                normalize_aspect=normalize_aspect,
                generate_thumbnail=generate_thumbnail,
                resize_width=resize_width,
                resize_height=resize_height,
                target_aspect_ratio=target_aspect_ratio,
            )
            
            if result["success"]:
                _LOGGER.info("Video processed successfully: %s", video_path)
                hass.bus.async_fire(
                    f"{DOMAIN}_video_processing_success",
                    result,
                )
            else:
                _LOGGER.error(
                    "Video processing failed: %s - %s",
                    video_path,
                    result.get("error", "Unknown error"),
                )
                hass.bus.async_fire(
                    f"{DOMAIN}_video_processing_failed",
                    result,
                )
        except Exception as err:
            _LOGGER.exception("Unexpected error processing video: %s", video_path)
            hass.bus.async_fire(
                f"{DOMAIN}_video_processing_failed",
                {
                    "video_path": video_path,
                    "error": str(err),
                },
            )
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_NORMALIZE_VIDEO,
        handle_normalize_video,
        schema=SERVICE_NORMALIZE_VIDEO_SCHEMA,
    )
    
    _LOGGER.debug("Video Normalizer service registered")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Video Normalizer integration")
    
    # Unregister the service
    hass.services.async_remove(DOMAIN, SERVICE_NORMALIZE_VIDEO)
    
    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Remove processor if it's the last entry
        if not any(
            key for key in hass.data[DOMAIN].keys() if key != "processor"
        ):
            hass.data[DOMAIN].pop("processor", None)
    
    return True
