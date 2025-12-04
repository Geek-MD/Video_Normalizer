# Video Normalizer Integration

## Overview

Video Normalizer is a custom integration for Home Assistant that normalizes video aspect ratios from downloaded content using the Downloader integration.

## Technical Details

### Dependencies

This integration has a hard dependency on the [Downloader](https://www.home-assistant.io/integrations/downloader/) integration. During setup:

1. The integration checks if Downloader is installed and loaded
2. Validates that Downloader is properly configured
3. Extracts the download directory path from Downloader's configuration
4. Aborts setup with a user-friendly error message if any validation fails

### Configuration Flow

The integration uses Home Assistant's config flow for setup:

- **Step 1:** User initiates integration setup from the UI
- **Step 2:** System validates Downloader integration is available
- **Step 3:** System extracts Downloader's download directory
- **Step 4:** Configuration is saved with the download directory path

### Error Handling

The integration provides specific error messages for different scenarios:

- **downloader_not_installed:** Shown when Downloader integration is not installed or not loaded
- **downloader_not_configured:** Shown when Downloader is installed but not properly configured
- **unknown:** Shown for unexpected errors (logged for debugging)

All error messages are available in both English and Spanish.

### Directory Usage

Video Normalizer uses the same download directory as configured in the Downloader integration. This ensures:

- Consistent file locations across integrations
- No need for duplicate directory configuration
- Seamless integration with existing Downloader workflows

## Development

### File Structure

```
custom_components/video_normalizer/
├── __init__.py           # Integration setup and entry point
├── config_flow.py        # Configuration flow with Downloader validation
├── const.py              # Constants and configuration keys
├── manifest.json         # Integration metadata
├── strings.json          # Spanish translations (default)
└── translations/
    └── en.json          # English translations
```

### Testing

To test the integration:

1. Ensure Home Assistant is running
2. Install and configure the Downloader integration first
3. Add the Video Normalizer integration through the UI
4. Verify it correctly detects Downloader and uses its directory

To test error scenarios:

1. Try adding Video Normalizer without Downloader installed
2. Verify the error message is displayed correctly
3. Install Downloader and retry
