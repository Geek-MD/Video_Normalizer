# Video Normalizer

Home Assistant custom integration that normalizes aspect ratio of videos downloaded using the Downloader integration.

## Requirements

This integration requires the [Downloader](https://www.home-assistant.io/integrations/downloader/) integration to be installed and configured in Home Assistant. Video Normalizer uses the same download directory as configured in the Downloader integration.

## Installation

1. Copy the `custom_components/video_normalizer` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click the + button to add a new integration
5. Search for "Video Normalizer"
6. Follow the configuration steps

**Note:** If the Downloader integration is not installed or configured, the setup process will alert you and abort the configuration.

## Configuration

The integration will automatically detect and use the download directory configured in the Downloader integration. No additional configuration is required.

## Features

- Automatic detection of Downloader integration
- Uses the same download directory as Downloader
- Emits automation-friendly events on video processing success or failure
- Easy setup through the Home Assistant UI
