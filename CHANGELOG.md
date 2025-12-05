# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
