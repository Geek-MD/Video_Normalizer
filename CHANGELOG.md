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
