[![Geek-MD - Video Normalizer](https://img.shields.io/static/v1?label=Geek-MD&message=Video%20Normalizer&color=blue&logo=github)](https://github.com/Geek-MD/Video_Normalizer)
[![Stars](https://img.shields.io/github/stars/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)
[![Forks](https://img.shields.io/github/forks/Geek-MD/Video_Normalizer?style=social)](https://github.com/Geek-MD/Video_Normalizer)

[![GitHub Release](https://img.shields.io/github/release/Geek-MD/Video_Normalizer?include_prereleases&sort=semver&color=blue)](https://github.com/Geek-MD/Video_Normalizer/releases)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/Geek-MD/Video_Normalizer/blob/main/LICENSE)
[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom%20Repository-blue)](https://hacs.xyz/)

[![Ruff + Mypy + Hassfest](https://github.com/Geek-MD/Video_Normalizer/actions/workflows/validate.yml/badge.svg)](https://github.com/Geek-MD/Video_Normalizer/actions/workflows/validate.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

<img width="200" height="200" alt="image" src="https://github.com/Geek-MD/Video_Normalizer/blob/main/logo.png?raw=true" />

# Video Normalizer

Home Assistant custom integration that normalizes aspect ratio of videos and provides flexible video processing capabilities.

## Requirements

This integration **requires** the [Downloader](https://www.home-assistant.io/integrations/downloader/) integration to be installed and configured first. Video Normalizer uses Downloader's configuration to automatically detect the download directory where videos are processed.

## Installation

### HACS (Recommended)

1. **Install Downloader first** (required dependency):
   - Go to Settings > Devices & Services
   - Click "+ Add Integration"
   - Search for "Downloader" and install it
   - Configure the download directory

2. Open HACS in your Home Assistant instance
3. Click on "Integrations"
4. Click the three dots in the top right corner and select "Custom repositories"
5. Add the repository URL: `https://github.com/Geek-MD/Video_Normalizer`
6. Select "Integration" as the category
7. Click "Add"
8. Search for "Video Normalizer" in HACS
9. Click "Download"
10. Restart Home Assistant
11. Go to Settings > Devices & Services
12. Click the + button to add a new integration
13. Search for "Video Normalizer"
14. Follow the configuration steps

### Manual Installation

1. **Install Downloader first** (required dependency):
   - Go to Settings > Devices & Services
   - Click "+ Add Integration"
   - Search for "Downloader" and install it
   - Configure the download directory

2. Copy the `custom_components/video_normalizer` directory to your Home Assistant `custom_components` directory
3. Restart Home Assistant
4. Go to Settings > Devices & Services
5. Click the + button to add a new integration
6. Search for "Video Normalizer"
7. Follow the configuration steps

**Note:** The setup wizard will automatically detect and use the download directory configured in your Downloader integration.

## Configuration

**Note:** Video Normalizer can only be configured once per Home Assistant instance. This ensures proper service and sensor management.

**Prerequisite:** The Downloader integration must be installed and configured before setting up Video Normalizer.

During setup, you'll need to configure:
- **Download directory**: Where videos to be processed are located. This field will be automatically pre-filled from your Downloader integration configuration.
- **Processing timeout** (optional, default: 300 seconds / 5 minutes): Maximum time to wait for video processing to complete. Optimized for Home Assistant Green hardware specifications (Rockchip RK3566, 4 GB RAM). Increase this value if you frequently process longer or higher-resolution videos.

## Features

- **Status Sensor** - Monitor the integration's processing state with a sensor entity that tracks:
  - Current state: `working` or `idle`
  - Last job result: `success`, `skipped`, or `failed`
  - Timestamp of last state change (server local time)
  - List of processes performed (resize, normalize_aspect, embed_thumbnail, etc.)
- Optional Downloader integration detection and auto-configuration
- **Simplified output configuration** - specify a single output file path or overwrite the original
- **Smart video analysis** - automatically detects if video needs processing (aspect ratio, thumbnail, dimensions)
- **Automatic aspect ratio normalization** for all videos to prevent square or distorted previews in Telegram and mobile players
- **Automatic thumbnail generation and embedding** to force Telegram to use the correct video preview
- **Optional video resizing** (width/height) if dimensions differ
- **Intelligent skip logic** - skips processing if video already meets requirements (unless resize is requested)
- **Robust detection of video dimensions** using ffprobe (JSON) with ffmpeg -i fallback
- **Processing timeout protection** - configurable timeout (default: 5 minutes) prevents indefinite hangs on corrupted or extremely large files
- **Performance logging** - logs elapsed time for all processing operations to help optimize timeout settings
- Emits automation-friendly events on video processing success, failure, or skip
- Easy setup through the Home Assistant UI

## Services

### video_normalizer.normalize_video

Process a video file with normalization operations.

**Parameters:**
- `input_file_path` (required): Full path to the input video file including filename (e.g., "/media/ring/ring.mp4")
- `output_file_path` (optional): Full path for the output video file including filename (e.g., "/media/processed/ring_normalized.mp4"). Only required when `overwrite` is false
- `overwrite` (optional, default: false): Whether to overwrite the original file. When true, `output_file_path` is ignored
- `normalize_aspect` (optional, default: true): Whether to normalize the aspect ratio to 16:9
- `generate_thumbnail` (optional, default: true): Whether to generate and embed a thumbnail
- **resize_width** (optional): Target width for resizing (maintains aspect ratio if only one dimension specified)
- **resize_height** (optional): Target height for resizing (maintains aspect ratio if only one dimension specified)
- **target_aspect_ratio** (optional, default: 1.777): Target aspect ratio as a decimal (e.g., 1.777 for 16:9, 1.333 for 4:3)
- **timeout** (optional, default: 300): Maximum time in seconds to wait for processing to complete. If processing takes longer, it will be terminated. Default of 5 minutes is optimized for Home Assistant Green. Increase for longer videos or higher resolutions.

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
          input_file_path: "{{ trigger.event.data.path }}"
          output_file_path: "{{ trigger.event.data.path | replace('.mp4', '_normalized.mp4') }}"
          normalize_aspect: true
          generate_thumbnail: true
```

## Entities

### Status Sensor

The integration provides a status sensor (`sensor.video_normalizer_status`) that tracks the processing state:

- **States:**
  - `working`: Currently processing a video
  - `idle`: Not processing, waiting for work

- **Attributes:**
  - `last_job`: Result of the last processing job (`success`, `skipped`, or `failed`)
  - `timestamp`: ISO 8601 timestamp of when the state last changed (server local time)
  - `processes`: List of processes performed in the last job (e.g., `["resize", "normalize_aspect", "embed_thumbnail"]`)

**Example automation using the sensor:**

```yaml
automation:
  - alias: "Notify when video processing completes"
    trigger:
      - platform: state
        entity_id: sensor.video_normalizer_status
        from: "working"
        to: "idle"
    action:
      - service: notify.mobile_app
        data:
          title: "Video Processing Complete"
          message: >
            Result: {{ state_attr('sensor.video_normalizer_status', 'last_job') }}
            Processes: {{ state_attr('sensor.video_normalizer_status', 'processes') | join(', ') }}
```

## Events

The service fires a single event that can be used in automations:
- `video_normalizer_video_processing_finished`: Fired when video processing completes, regardless of the result. The result is available in the event data under the `result` field, which can be `success`, `skipped`, or `failed`. Additional information about the processing is available in the sensor state attributes.

## Service Lifecycle

When the `video_normalizer.normalize_video` service is called, it follows a specific lifecycle to ensure proper operation and state management:

1. **Process Video**: The video is processed according to the specified parameters (resize, normalize aspect ratio, generate thumbnail, etc.)
2. **Fire Event**: A Home Assistant event (`video_normalizer_video_processing_finished`) is fired to notify automations of the processing completion. The event includes a `result` field with the value `success`, `skipped`, or `failed`
3. **Update Sensor**: The status sensor is updated to `idle` state with the appropriate result (`success`, `skipped`, or `failed`)
4. **Cleanup**: Temporary files created during processing are removed

This order ensures that:
- Automations receive events before the sensor state changes, allowing them to react to the event first
- The sensor state accurately reflects when processing is complete before cleanup begins
- Temporary files are cleaned up only after all state updates and notifications are complete

**Example of lifecycle in an automation:**

```yaml
automation:
  - alias: "Process video and send notification"
    trigger:
      - platform: event
        event_type: video_normalizer_video_processing_finished
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.result == 'success' }}"
    action:
      # This action runs immediately after processing, before sensor updates
      - service: notify.mobile_app
        data:
          title: "Video Ready"
          message: "Processing complete for {{ trigger.event.data.video_path }}"
  
  - alias: "Handle video processing failures"
    trigger:
      - platform: event
        event_type: video_normalizer_video_processing_finished
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.result == 'failed' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Video Processing Failed"
          message: "Error: {{ trigger.event.data.error }}"
      
  - alias: "Monitor sensor state change"
    trigger:
      - platform: state
        entity_id: sensor.video_normalizer_status
        to: "idle"
    action:
      # This action runs after the event has been fired
      - service: notify.mobile_app
        data:
          title: "Video Normalizer Idle"
          message: "Status: {{ state_attr('sensor.video_normalizer_status', 'last_job') }}"
```

## Requirements

This integration requires:
- FFmpeg to be available in the Home Assistant environment (typically pre-installed)
- Recommended: The [Downloader](https://www.home-assistant.io/integrations/downloader/) integration for automatic video downloads (optional)

---

<div align="center">
  
💻 **Proudly developed with GitHub Copilot** 🚀

</div>
