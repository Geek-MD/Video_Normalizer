[![Geek-MD - Video Normalizer](https://img.shields.io/static/v1?label=Geek-MD&message=Video%20Normalizer&color=blue&logo=github)](https://github.com/Geek-MD/Video_Normalizer)
[![Stars](https://img.shields.io/github/stars/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)
[![Forks](https://img.shields.io/github/forks/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/Video_Normalizer?include_prereleases&sort=semver&color=blue)](https://github.com/Geek-MD/Video_Normalizer/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Geek-MD/Video_Normalizer/blob/main/LICENSE)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-blue)](https://hacs.xyz/)

# Video Normalizer

Home Assistant custom integration that normalizes aspect ratio of videos downloaded using the Downloader integration.

## Requirements

This integration requires the [Downloader](https://www.home-assistant.io/integrations/downloader/) integration to be installed and configured in Home Assistant. Video Normalizer uses the same download directory as configured in the Downloader integration.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add the repository URL: `https://github.com/Geek-MD/Video_Normalizer`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Video Normalizer" in HACS
8. Click "Download"
9. Restart Home Assistant
10. Go to Settings > Devices & Services
11. Click the + button to add a new integration
12. Search for "Video Normalizer"
13. Follow the configuration steps

### Manual Installation

1. Copy the `custom_components/video_normalizer` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services
4. Click the + button to add a new integration
5. Search for "Video Normalizer"
6. Follow the configuration steps

**Note:** If the Downloader integration is not installed or configured, the setup process will alert you and abort the configuration.

## Configuration

The integration will automatically detect and use the download directory configured in the Downloader integration. No additional configuration is required.

## Features

- Automatic detection of Downloader integration
- Uses the same download directory as Downloader
- **Automatic aspect ratio normalization** for all downloaded videos to prevent square or distorted previews in Telegram and mobile players
- **Automatic thumbnail generation and embedding** to force Telegram to use the correct video preview
- **Optional video resizing subprocess** (width/height) if dimensions differ
- **Robust detection of video dimensions** using ffprobe (JSON) with ffmpeg -i fallback
- Emits automation-friendly events on video processing success or failure
- Easy setup through the Home Assistant UI

## Services

### video_normalizer.normalize_video

Process a video file with normalization operations.

**Parameters:**
- `video_path` (required): Path to the video file to process
- `normalize_aspect` (optional, default: true): Whether to normalize the aspect ratio to 16:9
- `generate_thumbnail` (optional, default: true): Whether to generate and embed a thumbnail
- `resize_width` (optional): Target width for resizing (maintains aspect ratio if only one dimension specified)
- `resize_height` (optional): Target height for resizing (maintains aspect ratio if only one dimension specified)
- `target_aspect_ratio` (optional, default: 1.777): Target aspect ratio as a decimal (e.g., 1.777 for 16:9, 1.333 for 4:3)

**Example automation:**

```yaml
automation:
  - alias: "Normalize Downloaded Videos"
    trigger:
      - platform: event
        event_type: folder_watcher
        event_data:
          event_type: created
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.file.endswith(('.mp4', '.avi', '.mov', '.mkv')) }}"
    action:
      - service: video_normalizer.normalize_video
        data:
          video_path: "{{ trigger.event.data.path }}"
          normalize_aspect: true
          generate_thumbnail: true
```

## Events:

The service fires events that can be used in automations:
- `video_normalizer_video_processing_success`: Fired when video processing completes successfully
- `video_normalizer_video_processing_failed`: Fired when video processing fails

## Requirements

This integration requires:
- The [Downloader](https://www.home-assistant.io/integrations/downloader/) integration to be installed and configured in Home Assistant
- FFmpeg to be available in the Home Assistant environment (typically pre-installed)

## Release Process

This repository uses automated release creation based on the version specified in `custom_components/video_normalizer/manifest.json`. 

Releases are created with the format `vX.X.X` (e.g., `v0.2.0`) and can be triggered in two ways:
1. **Automatically**: When changes to `manifest.json` are pushed to the main branch
2. **Manually**: By running the "Create Release" workflow from the Actions tab

The workflow will check if a release with the current version already exists before creating a new one.

---

<div align="center">
  
💻 **Proudly developed with GitHub Copilot** 🚀

</div>
