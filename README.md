[![Geek-MD - Video Normalizer](https://img.shields.io/static/v1?label=Geek-MD&message=Video%20Normalizer&color=blue&logo=github)](https://github.com/Geek-MD/Video_Normalizer)
[![Stars](https://img.shields.io/github/stars/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)
[![Forks](https://img.shields.io/github/forks/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/Video_Normalizer?include_prereleases&sort=semver&color=blue)](https://github.com/Geek-MD/Video_Normalizer/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Geek-MD/Video_Normalizer/blob/main/LICENSE)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-blue)](https://hacs.xyz/)

[![Ruff + Mypy + Hassfest](https://github.com/Geek-MD/Video_Normalizer/actions/workflows/validate.yml/badge.svg)](https://github.com/Geek-MD/Video_Normalizer/actions/workflows/validate.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

# Video Normalizer

Home Assistant custom integration that normalizes aspect ratio of videos and provides flexible video processing capabilities.

## Requirements

This integration works independently but is recommended to be used with the [Downloader](https://www.home-assistant.io/integrations/downloader/) integration for automatic video downloads. If Downloader is installed, Video Normalizer will auto-detect and use its download directory configuration.

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

**Note:** The setup wizard will recommend installing the Downloader integration if it's not already installed, but it's not required. If Downloader is installed, its configuration will be automatically detected.

## Configuration

During setup, you'll need to configure the download directory where videos are located. If the Downloader integration is installed, this field will be automatically pre-filled with its configured directory.

## Features

- Optional Downloader integration detection and auto-configuration
- **Flexible output path and naming** - specify custom output directory and filename, or overwrite the original
- **Automatic aspect ratio normalization** for all videos to prevent square or distorted previews in Telegram and mobile players
- **Automatic thumbnail generation and embedding** to force Telegram to use the correct video preview
- **Optional video resizing** (width/height) if dimensions differ
- **Robust detection of video dimensions** using ffprobe (JSON) with ffmpeg -i fallback
- Emits automation-friendly events on video processing success or failure
- Easy setup through the Home Assistant UI

## Services

### video_normalizer.normalize_video

Process a video file with normalization operations.

**Parameters:**
- `video_path` (required): Path to the video file to process
- `output_path` (optional): Directory where the processed video will be saved (defaults to same directory as input)
- `output_name` (optional): Name for the output video file (defaults to same name as input)
- `overwrite` (optional, default: false): Whether to overwrite the original file
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
- FFmpeg to be available in the Home Assistant environment (typically pre-installed)
- Recommended: The [Downloader](https://www.home-assistant.io/integrations/downloader/) integration for automatic video downloads (optional)

---

<div align="center">
  
💻 **Proudly developed with GitHub Copilot** 🚀

</div>
