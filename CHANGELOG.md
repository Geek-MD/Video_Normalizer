# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2025-12-16

### Added

- **Processing Timeout**: New timeout parameter to prevent indefinite hangs during video processing
  - Configurable timeout parameter in integration setup (default: 300 seconds / 5 minutes)
  - Optional timeout parameter in `normalize_video` service call to override configured default
  - Automatically terminates processing if it exceeds the timeout
  - Logs timeout events with clear error messages
  - Fires `video_normalizer_video_processing_failed` event with timeout error details
  - Sensor updates to "failed" state when timeout occurs
- **Performance Logging**: Added elapsed time tracking for all video processing operations
  - Logs total processing time for every video (success, skipped, failed, timeout)
  - Format: "Elapsed time: X.XX seconds - Result: [success|skipped|failed]"
  - Helps gather real-world performance data to optimize timeout defaults in future versions
  - Provides visibility into processing performance on different hardware
- Default timeout of 300 seconds (5 minutes) optimized for Home Assistant Green hardware:
  - Home Assistant Green specs: Rockchip RK3566 (Quad-core ARM Cortex-A55 @ 1.8 GHz), 4 GB RAM
  - Typical processing times on Home Assistant Green:
    - 30-second 720p video: ~30-60 seconds
    - 2-minute 1080p video: ~2-3 minutes
    - 5-minute 1080p video: ~4-8 minutes
  - 5-minute timeout handles most surveillance/doorbell videos while preventing indefinite hangs

### Changed

- Updated integration version to 0.5.1 in manifest.json
- Enhanced service handler to wrap video processing with `asyncio.wait_for()` for timeout enforcement
- Configuration flow now includes timeout field with validation (minimum 1 second)
- Integration setup stores timeout configuration for use across service calls
- Improved logging messages to include elapsed time and result status for all operations
- Enhanced error logging with detailed timing information for troubleshooting

### Technical

- Added `CONF_TIMEOUT` and `DEFAULT_TIMEOUT` constants to const.py
- Updated service schema to accept optional timeout parameter
- Improved error handling with specific timeout exception catching
- Added `time` module import for performance tracking
- Removed redundant validation logic (handled by voluptuous schema)
- All code passes ruff linting and mypy type checking
- CodeQL security scan: 0 vulnerabilities
- Updated translations (English and Spanish) to include timeout configuration
- Updated README.md with timeout documentation

## [0.5.0] - 2025-12-16

### Added

- **Status Sensor**: New sensor entity to track the Video Normalizer service status
  - Sensor states: `working` (when processing video) and `idle` (when processing complete or not running)
  - Sensor attributes:
    - `last_job`: Result of the last job ("success", "skipped", or "failed")
    - `timestamp`: ISO 8601 timestamp of when the state last changed (using Home Assistant server local time)
    - `processes`: List of subprocesses that were performed (e.g., ["resize", "normalize_aspect", "embed_thumbnail"])
  - Dynamic icon that changes based on state (video-check when working, video-check-outline when idle)
- Enhanced logging for sensor state changes

### Changed

- **BREAKING**: Service parameter names updated for better clarity:
  - `video_path` renamed to `input_file_path` - Now expects full file path including filename (e.g., "/media/ring/ring.mp4")
  - `output_path` and `output_name` consolidated into single `output_file_path` parameter - Expects full file path including filename (e.g., "/media/processed/ring_normalized.mp4")
  - `output_file_path` is only required when `overwrite` is false
  - When `overwrite` is true, the input file path is used automatically
- Updated integration version to 0.5.0 in manifest.json
- Service handler now updates sensor state during video processing
- Sensor platform automatically registered during integration setup
- Timestamps now use Home Assistant server local time

### Technical

- New sensor.py module with VideoNormalizerSensor class
- Integration follows Home Assistant sensor entity best practices
- Service schema updated to reflect new parameter structure
- All code passes ruff linting and mypy type checking
- Improved service parameter handling and validation
- Added entity translations for sensor in English and Spanish

## [0.4.1] - 2025-12-05

### Enhanced

- Improved logging visibility in Home Assistant logs - All important operations now generate INFO-level log entries that are visible in Home Assistant logs by default
- Video dimension detection now logs when starting and upon successful detection
- Thumbnail generation operations now log progress and completion
- Thumbnail embedding operations now log progress and completion
- Video analysis phase now logs the reasons when processing is needed or when skipped
- Integration setup and service registration now use INFO level for better visibility
- Integration unload operations now logged at INFO level

### Changed

- Promoted key operational logs from DEBUG to INFO level to ensure visibility in Home Assistant logs without requiring DEBUG log configuration
- Updated integration version to 0.4.1 in manifest.json

### Technical

- All changes maintain backward compatibility
- Code passes ruff linting validation
- Code passes mypy type checking validation
- Code formatting improved following review suggestions

## [0.4.0] - 2025-12-05

### Added

- **Intelligent video analysis**: The system now automatically analyzes each video before processing to determine if it actually needs changes
  - Verifies if the aspect ratio is correct (0.01 tolerance)
  - Detects if the video already has an embedded thumbnail
  - Checks if dimensions match the resize target
- **Smart skip logic**: When a video already meets all requirements, processing is automatically skipped to save time and resources
  - Applied only when there's no resize request
  - If resize is requested, the full process always executes
- **New automation event**: `video_normalizer_video_skipped`
  - Fires when processing is skipped because the video is already correct
  - Includes complete analysis data in the event payload
  - Allows automations to distinguish between successful processing, skipped, or failed

### Changed

- Extracted `ASPECT_RATIO_TOLERANCE` constant for better maintainability
- Optimized aspect ratio calculation to avoid code duplication
- Analysis executed before file operations to minimize unnecessary I/O
- Improved informative logs about processing skip reasons

### Technical

- Validated with Ruff (no errors)
- Validated with Mypy (no type errors)
- CodeQL analysis (0 vulnerabilities)
- Hassfest compatible

## [0.3.0] - 2025-12-04

### Added

- **Flexible output path and naming**: New parameters for custom output directory and filename
  - `output_path` parameter: Specify custom output directory (defaults to same directory as input)
  - `output_name` parameter: Specify custom filename (defaults to same name as input)
  - `overwrite` option: Choose whether to overwrite the original file (default: false)
- **Optional Downloader integration**: Downloader is now recommended but not required
  - Setup wizard shows recommendation dialog for installing Downloader
  - Auto-detects and uses Downloader configuration when available
  - Works independently without Downloader if desired

### Changed

- Removed hard requirement for Downloader integration
- Updated configuration flow to show recommendation instead of requirement
- Improved setup wizard with better user guidance

### Technical

- Added GitHub Actions workflow for automated validation
- Full CI/CD pipeline with ruff, mypy, and hassfest
- Added validation badges to README
- Created Spanish translation (es.json)
- All validation checks pass
- Dependencies simplified for reliable CI/CD

## [0.2.0] - 2025-12-04

### Added

- **Automated release workflow**: GitHub Actions workflow for creating releases automatically
  - Extracts version from manifest.json
  - Creates releases with `vX.X.X` tag format
  - Verifies version changes to prevent unnecessary releases
  - Prevents duplicate releases by checking existing tags
- **Release documentation**: Added "Release Process" section to README

### Changed

- Implemented version-based release automation
- Added safeguards for release creation (file path filter, version comparison, tag existence check)

### Technical

- Workflow triggers on manifest.json changes or manual dispatch
- Three layers of protection against duplicate releases
