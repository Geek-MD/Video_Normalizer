# Video Normalizer Integration

## Overview

Video Normalizer is a custom integration for Home Assistant that provides automatic video normalization services including aspect ratio correction, thumbnail generation, and optional resizing for downloaded content.

## Features

### 1. Automatic Aspect Ratio Normalization
- Prevents square or distorted video previews in Telegram and mobile players
- Default target aspect ratio: 16:9 (configurable)
- Adds black padding (letterboxing or pillarboxing) as needed
- Maintains original video quality

### 2. Automatic Thumbnail Generation and Embedding
- Extracts a frame from the video at a specified timestamp (default: 1 second)
- Embeds the thumbnail into the video file metadata
- Forces Telegram and other apps to use the correct video preview
- Automatically cleans up temporary thumbnail files

### 3. Robust Video Dimension Detection
- Primary method: ffprobe with JSON output for accurate parsing
- Fallback method: ffmpeg -i with regex parsing
- Returns detailed video information including:
  - Width and height
  - Aspect ratio
  - Codec information
  - Duration

### 4. Optional Video Resizing
- Resize by width only (maintains aspect ratio)
- Resize by height only (maintains aspect ratio)
- Resize to specific dimensions (width and height)
- Uses high-quality encoding settings (libx264, CRF 23)

## Technical Details

### Dependencies

This integration has dependencies on:
1. The [Downloader](https://www.home-assistant.io/integrations/downloader/) integration
2. FFmpeg binary (typically pre-installed in Home Assistant)
3. FFprobe binary (part of FFmpeg)

During setup:
1. The integration checks if Downloader is installed and loaded
2. Validates that Downloader is properly configured
3. Extracts the download directory path from Downloader's configuration
4. Aborts setup with a user-friendly error message if any validation fails

### Service: normalize_video

The main service provided by this integration processes videos with the following parameters:

**Required:**
- `video_path`: Full path to the video file

**Optional:**
- `normalize_aspect`: Enable aspect ratio normalization (default: true)
- `generate_thumbnail`: Enable thumbnail generation and embedding (default: true)
- `resize_width`: Target width in pixels (maintains aspect ratio if height not specified)
- `resize_height`: Target height in pixels (maintains aspect ratio if width not specified)
- `target_aspect_ratio`: Target aspect ratio as decimal (default: 1.777 for 16:9)

### Processing Pipeline

When a video is processed, the following operations occur in order:

1. **Validation**: Check if video file exists
2. **Dimension Detection**: Get video dimensions using ffprobe/ffmpeg
3. **Resizing** (if requested): Resize video to target dimensions
4. **Aspect Ratio Normalization** (if enabled): Add padding to achieve target aspect ratio
5. **Thumbnail Generation** (if enabled): Extract frame from video
6. **Thumbnail Embedding** (if enabled): Embed thumbnail in video metadata

All operations use temporary files and atomic replacements to prevent data loss.

### Events

The integration fires automation-friendly events:

**video_normalizer_video_processing_success:**
```yaml
event_data:
  video_path: "/path/to/video.mp4"
  success: true
  operations:
    resize: true
    normalize_aspect: true
    generate_thumbnail: true
    embed_thumbnail: true
  original_dimensions:
    width: 1920
    height: 1440
    aspect_ratio: 1.333
  final_dimensions:
    width: 1920
    height: 1080
    aspect_ratio: 1.777
```

**video_normalizer_video_processing_failed:**
```yaml
event_data:
  video_path: "/path/to/video.mp4"
  success: false
  error: "Error message"
```

### Configuration Flow

The integration uses Home Assistant's config flow for setup:

- **Step 1:** User initiates integration setup from the UI
- **Step 2:** System validates Downloader integration is available
- **Step 3:** System extracts Downloader's download directory
- **Step 4:** Configuration is saved with the download directory path
- **Step 5:** Video processing service is registered

### Error Handling

The integration provides specific error messages for different scenarios:

- **downloader_not_installed:** Shown when Downloader integration is not installed or not loaded
- **downloader_not_configured:** Shown when Downloader is installed but not properly configured
- **unknown:** Shown for unexpected errors (logged for debugging)

All error messages are available in both English and Spanish.

### Video Processing Error Handling

The video processor implements robust error handling:
- Temporary files are used for all operations
- Original files are only replaced after successful processing
- Failed operations clean up temporary files
- Detailed logging for debugging
- Operations continue even if individual steps fail
- Events are fired for both success and failure

## Development

### File Structure

```
custom_components/video_normalizer/
├── __init__.py           # Integration setup, service registration
├── video_processor.py    # Video processing logic
├── config_flow.py        # Configuration flow with Downloader validation
├── const.py              # Constants and configuration keys
├── manifest.json         # Integration metadata
├── services.yaml         # Service definitions
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
5. Call the `video_normalizer.normalize_video` service with a test video

To test error scenarios:

1. Try adding Video Normalizer without Downloader installed
2. Verify the error message is displayed correctly
3. Install Downloader and retry

### Example Automation

```yaml
automation:
  - alias: "Auto-normalize downloaded videos"
    description: "Automatically normalize videos when downloaded"
    trigger:
      - platform: event
        event_type: folder_watcher
        event_data:
          event_type: created
    condition:
      - condition: template
        value_template: >
          {{ trigger.event.data.file.endswith(('.mp4', '.avi', '.mov', '.mkv')) }}
    action:
      - service: video_normalizer.normalize_video
        data:
          video_path: "{{ trigger.event.data.path }}"
          normalize_aspect: true
          generate_thumbnail: true
      - wait_for_trigger:
          - platform: event
            event_type: video_normalizer_video_processing_success
          - platform: event
            event_type: video_normalizer_video_processing_failed
        timeout: "00:10:00"
      - choose:
          - conditions:
              - condition: template
                value_template: >
                  {{ wait.trigger.event.event_type == 'video_normalizer_video_processing_success' }}
            sequence:
              - service: notify.telegram
                data:
                  message: "Video normalized successfully: {{ wait.trigger.event.data.video_path }}"
          - conditions:
              - condition: template
                value_template: >
                  {{ wait.trigger.event.event_type == 'video_normalizer_video_processing_failed' }}
            sequence:
              - service: notify.telegram
                data:
                  message: "Video normalization failed: {{ wait.trigger.event.data.error }}"
```

### Code Quality

The code follows Home Assistant development best practices:
- Async/await for all I/O operations
- Proper error handling and logging
- Type hints for better code clarity
- Atomic file operations to prevent data loss
- Cleanup of temporary files
- Integration with Home Assistant's event system
