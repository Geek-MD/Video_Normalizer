"""Video processing functionality for Video Normalizer integration."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VideoProcessor:
    """Handle video normalization operations."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """Initialize the video processor.
        
        Args:
            ffmpeg_path: Path to ffmpeg binary
            ffprobe_path: Path to ffprobe binary
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    async def get_video_dimensions(self, video_path: str) -> dict[str, Any]:
        """Get video dimensions using ffprobe with ffmpeg fallback.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information including width, height, and aspect ratio
        """
        # Try ffprobe first (JSON output)
        try:
            result = await self._get_dimensions_with_ffprobe(video_path)
            if result:
                return result
        except Exception as err:
            _LOGGER.debug(
                "ffprobe failed, trying ffmpeg fallback: %s", err
            )

        # Fallback to ffmpeg -i
        try:
            result = await self._get_dimensions_with_ffmpeg(video_path)
            if result:
                return result
        except Exception as err:
            _LOGGER.error(
                "Failed to get video dimensions for %s: %s", video_path, err
            )
            raise

        raise ValueError(f"Could not determine dimensions for {video_path}")

    async def _get_dimensions_with_ffprobe(
        self, video_path: str
    ) -> dict[str, Any] | None:
        """Get video dimensions using ffprobe JSON output.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information or None if failed
        """
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            video_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                _LOGGER.debug(
                    "ffprobe returned non-zero exit code: %s", stderr.decode()
                )
                return None

            data = json.loads(stdout.decode())
            streams = data.get("streams", [])
            
            if not streams:
                return None

            video_stream = streams[0]
            width = video_stream.get("width")
            height = video_stream.get("height")

            if not width or not height:
                return None

            aspect_ratio = width / height

            return {
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "codec": video_stream.get("codec_name"),
                "duration": video_stream.get("duration"),
            }

        except (json.JSONDecodeError, KeyError, TypeError) as err:
            _LOGGER.debug("Failed to parse ffprobe output: %s", err)
            return None

    async def _get_dimensions_with_ffmpeg(
        self, video_path: str
    ) -> dict[str, Any] | None:
        """Get video dimensions using ffmpeg -i output parsing.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information or None if failed
        """
        cmd = [self.ffmpeg_path, "-i", video_path]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            # ffmpeg -i outputs to stderr
            output = stderr.decode()

            # Parse the output for video stream information
            # Look for pattern like "Stream #0:0: Video: ... 1920x1080"
            pattern = r"Stream.*Video.*?(\d{2,5})x(\d{2,5})"
            match = re.search(pattern, output)

            if not match:
                return None

            width = int(match.group(1))
            height = int(match.group(2))
            aspect_ratio = width / height

            return {
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
            }

        except (ValueError, AttributeError) as err:
            _LOGGER.debug("Failed to parse ffmpeg output: %s", err)
            return None

    async def generate_thumbnail(
        self, video_path: str, thumbnail_path: str, timestamp: str = "00:00:01"
    ) -> bool:
        """Generate a thumbnail from video at specified timestamp.
        
        Args:
            video_path: Path to the video file
            thumbnail_path: Path where thumbnail should be saved
            timestamp: Timestamp for thumbnail (format: HH:MM:SS)
            
        Returns:
            True if thumbnail was generated successfully
        """
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            "-y",  # Overwrite output file
            thumbnail_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to generate thumbnail: %s", stderr.decode()
                )
                return False

            if os.path.exists(thumbnail_path):
                _LOGGER.debug("Thumbnail generated successfully at %s", thumbnail_path)
                return True
            
            return False

        except Exception as err:
            _LOGGER.error("Error generating thumbnail: %s", err)
            return False

    async def embed_thumbnail(self, video_path: str, thumbnail_path: str) -> bool:
        """Embed thumbnail into video file metadata.
        
        Args:
            video_path: Path to the video file
            thumbnail_path: Path to the thumbnail image
            
        Returns:
            True if thumbnail was embedded successfully
        """
        # Create output path with temp suffix
        output_path = f"{video_path}.tmp"

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-i", thumbnail_path,
            "-map", "0",
            "-map", "1",
            "-c", "copy",
            "-disposition:v:1", "attached_pic",
            "-y",
            output_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to embed thumbnail: %s", stderr.decode()
                )
                # Clean up temp file if it exists
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False

            # Replace original with the new file
            os.replace(output_path, video_path)
            _LOGGER.debug("Thumbnail embedded successfully into %s", video_path)
            return True

        except Exception as err:
            _LOGGER.error("Error embedding thumbnail: %s", err)
            # Clean up temp file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            return False

    async def normalize_aspect_ratio(
        self, video_path: str, target_aspect_ratio: float | None = None
    ) -> bool:
        """Normalize video aspect ratio to prevent square or distorted previews.
        
        Args:
            video_path: Path to the video file
            target_aspect_ratio: Target aspect ratio (default: 16/9 = 1.777...)
            
        Returns:
            True if normalization was successful
        """
        if target_aspect_ratio is None:
            target_aspect_ratio = 16 / 9  # Default to 16:9

        # Get current dimensions
        try:
            info = await self.get_video_dimensions(video_path)
        except Exception as err:
            _LOGGER.error("Failed to get video dimensions: %s", err)
            return False

        current_aspect_ratio = info["aspect_ratio"]
        
        # Check if normalization is needed (with small tolerance)
        if abs(current_aspect_ratio - target_aspect_ratio) < 0.01:
            _LOGGER.debug(
                "Video already has correct aspect ratio: %.3f", current_aspect_ratio
            )
            return True

        _LOGGER.info(
            "Normalizing aspect ratio from %.3f to %.3f",
            current_aspect_ratio,
            target_aspect_ratio,
        )

        # Calculate new dimensions
        width = info["width"]
        height = info["height"]
        
        if current_aspect_ratio > target_aspect_ratio:
            # Video is wider, add padding top/bottom
            new_height = int(width / target_aspect_ratio)
            pad_height = new_height - height
            pad_top = pad_height // 2
            pad_bottom = pad_height - pad_top
            filter_complex = f"pad={width}:{new_height}:0:{pad_top}:black"
        else:
            # Video is taller, add padding left/right
            new_width = int(height * target_aspect_ratio)
            pad_width = new_width - width
            pad_left = pad_width // 2
            pad_right = pad_width - pad_left
            filter_complex = f"pad={new_width}:{height}:{pad_left}:0:black"

        # Create output path with temp suffix
        output_path = f"{video_path}.tmp"

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", filter_complex,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to normalize aspect ratio: %s", stderr.decode()
                )
                # Clean up temp file if it exists
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False

            # Replace original with the new file
            os.replace(output_path, video_path)
            _LOGGER.info("Aspect ratio normalized successfully for %s", video_path)
            return True

        except Exception as err:
            _LOGGER.error("Error normalizing aspect ratio: %s", err)
            # Clean up temp file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            return False

    async def resize_video(
        self, video_path: str, target_width: int | None = None, 
        target_height: int | None = None
    ) -> bool:
        """Resize video to specified dimensions.
        
        Args:
            video_path: Path to the video file
            target_width: Target width (None to maintain aspect ratio)
            target_height: Target height (None to maintain aspect ratio)
            
        Returns:
            True if resize was successful
        """
        if target_width is None and target_height is None:
            _LOGGER.warning("No target dimensions specified for resize")
            return False

        # Get current dimensions
        try:
            info = await self.get_video_dimensions(video_path)
        except Exception as err:
            _LOGGER.error("Failed to get video dimensions: %s", err)
            return False

        current_width = info["width"]
        current_height = info["height"]

        # Calculate target dimensions maintaining aspect ratio if needed
        if target_width and target_height:
            new_width = target_width
            new_height = target_height
        elif target_width:
            new_width = target_width
            new_height = int(target_width / (current_width / current_height))
        else:  # target_height only
            new_height = target_height
            new_width = int(target_height * (current_width / current_height))

        # Check if resize is needed
        if new_width == current_width and new_height == current_height:
            _LOGGER.debug("Video already has target dimensions")
            return True

        _LOGGER.info(
            "Resizing video from %dx%d to %dx%d",
            current_width, current_height, new_width, new_height
        )

        # Create output path with temp suffix
        output_path = f"{video_path}.tmp"

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", f"scale={new_width}:{new_height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to resize video: %s", stderr.decode()
                )
                # Clean up temp file if it exists
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False

            # Replace original with the new file
            os.replace(output_path, video_path)
            _LOGGER.info("Video resized successfully: %s", video_path)
            return True

        except Exception as err:
            _LOGGER.error("Error resizing video: %s", err)
            # Clean up temp file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            return False

    async def process_video(
        self,
        video_path: str,
        normalize_aspect: bool = True,
        generate_thumbnail: bool = True,
        resize_width: int | None = None,
        resize_height: int | None = None,
        target_aspect_ratio: float | None = None,
    ) -> dict[str, Any]:
        """Process video with all requested operations.
        
        Args:
            video_path: Path to the video file
            normalize_aspect: Whether to normalize aspect ratio
            generate_thumbnail: Whether to generate and embed thumbnail
            resize_width: Optional target width for resizing
            resize_height: Optional target height for resizing
            target_aspect_ratio: Optional target aspect ratio (default: 16/9)
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "video_path": video_path,
            "success": False,
            "operations": {},
        }

        # Validate video file exists
        if not os.path.exists(video_path):
            results["error"] = f"Video file not found: {video_path}"
            return results

        try:
            # Get initial video information
            info = await self.get_video_dimensions(video_path)
            results["original_dimensions"] = {
                "width": info["width"],
                "height": info["height"],
                "aspect_ratio": info["aspect_ratio"],
            }

            # Step 1: Resize if requested (do this before aspect ratio normalization)
            if resize_width or resize_height:
                resize_success = await self.resize_video(
                    video_path, resize_width, resize_height
                )
                results["operations"]["resize"] = resize_success
                if not resize_success:
                    _LOGGER.warning("Resize operation failed, continuing with other operations")

            # Step 2: Normalize aspect ratio
            if normalize_aspect:
                normalize_success = await self.normalize_aspect_ratio(
                    video_path, target_aspect_ratio
                )
                results["operations"]["normalize_aspect"] = normalize_success
                if not normalize_success:
                    _LOGGER.warning("Aspect ratio normalization failed, continuing with other operations")

            # Step 3: Generate and embed thumbnail
            if generate_thumbnail:
                # Generate thumbnail in the same directory as the video
                video_dir = os.path.dirname(video_path)
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                thumbnail_path = os.path.join(video_dir, f"{video_name}_thumb.jpg")

                thumbnail_success = await self.generate_thumbnail(
                    video_path, thumbnail_path
                )
                results["operations"]["generate_thumbnail"] = thumbnail_success

                if thumbnail_success:
                    embed_success = await self.embed_thumbnail(
                        video_path, thumbnail_path
                    )
                    results["operations"]["embed_thumbnail"] = embed_success

                    # Clean up standalone thumbnail file
                    try:
                        if os.path.exists(thumbnail_path):
                            os.remove(thumbnail_path)
                    except Exception as err:
                        _LOGGER.debug("Could not remove thumbnail file: %s", err)
                else:
                    results["operations"]["embed_thumbnail"] = False

            # Get final video information
            final_info = await self.get_video_dimensions(video_path)
            results["final_dimensions"] = {
                "width": final_info["width"],
                "height": final_info["height"],
                "aspect_ratio": final_info["aspect_ratio"],
            }

            # Consider success if at least one operation succeeded
            results["success"] = any(results["operations"].values())

        except Exception as err:
            _LOGGER.error("Error processing video %s: %s", video_path, err)
            results["error"] = str(err)

        return results
