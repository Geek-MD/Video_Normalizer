"""Video processing functionality for Video Normalizer integration."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from typing import Any

_LOGGER = logging.getLogger(__name__)


class VideoProcessor:
    """Handle video normalization operations."""
    
    # Tolerance for aspect ratio comparison
    ASPECT_RATIO_TOLERANCE = 0.01
    
    # Timeout for ffprobe operations (seconds)
    PROBE_TIMEOUT = 30
    
    # Timeout for individual ffmpeg operations (seconds)
    # This should be per-operation timeout, not total processing timeout
    FFMPEG_OPERATION_TIMEOUT = 300

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """Initialize the video processor.
        
        Args:
            ffmpeg_path: Path to ffmpeg binary
            ffprobe_path: Path to ffprobe binary
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def cleanup_temp_files(self, temp_files: list[str]) -> None:
        """Clean up temporary files after processing is complete.
        
        This should be called after the sensor state has been updated to idle,
        ensuring that the cleanup happens after the service completes.
        
        Args:
            temp_files: List of temporary file paths to remove
        """
        if not temp_files:
            return
            
        _LOGGER.debug("Cleaning up %d temporary file(s)", len(temp_files))
        
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    _LOGGER.debug("Removed temporary file: %s", temp_file)
            except Exception as err:
                _LOGGER.debug("Could not remove temp file %s: %s", temp_file, err)

    def cleanup_temp_files_by_video_path(self, video_path: str) -> None:
        """Clean up temporary files based on the original video path.
        
        This is used when processing fails or times out and we don't have
        the full list of temp files, but need to clean up any that may exist.
        
        Args:
            video_path: Original video file path
        """
        base_path, ext = os.path.splitext(video_path)
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # List of possible temp files that could be created
        possible_temp_files = [
            f"{base_path}.resize.tmp{ext}",
            f"{base_path}.normalize.tmp{ext}",
            f"{base_path}.thumbnail.tmp{ext}",
            os.path.join(video_dir, f"{video_name}_thumb.jpg"),
        ]
        
        _LOGGER.debug("Attempting cleanup of potential temp files for: %s", video_path)
        
        for temp_file in possible_temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    _LOGGER.debug("Removed temporary file: %s", temp_file)
            except Exception as err:
                _LOGGER.debug("Could not remove temp file %s: %s", temp_file, err)

    async def get_video_dimensions(self, video_path: str) -> dict[str, Any]:
        """Get video dimensions using ffprobe with ffmpeg fallback.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information including width, height, and aspect ratio
        """
        _LOGGER.info("Detecting video dimensions for: %s", video_path)

        # Try ffprobe first (JSON output)
        try:
            result = await self._get_dimensions_with_ffprobe(video_path)
            if result:
                _LOGGER.info(
                    "Video dimensions detected: %dx%d (aspect ratio: %.3f)",
                    result["width"], result["height"], result["aspect_ratio"]
                )
                return result
        except Exception as err:
            _LOGGER.debug(
                "ffprobe failed, trying ffmpeg fallback: %s", err
            )

        # Fallback to ffmpeg -i
        try:
            result = await self._get_dimensions_with_ffmpeg(video_path)
            if result:
                _LOGGER.info(
                    "Video dimensions detected (via ffmpeg): %dx%d (aspect ratio: %.3f)",
                    result["width"], result["height"], result["aspect_ratio"]
                )
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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.PROBE_TIMEOUT
            )

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

        except asyncio.TimeoutError:
            _LOGGER.debug("ffprobe timed out after %d seconds", self.PROBE_TIMEOUT)
            return None
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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.PROBE_TIMEOUT
            )

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

        except asyncio.TimeoutError:
            _LOGGER.debug("ffmpeg -i timed out after %d seconds", self.PROBE_TIMEOUT)
            return None
        except (ValueError, AttributeError) as err:
            _LOGGER.debug("Failed to parse ffmpeg output: %s", err)
            return None

    async def check_video_has_thumbnail(self, video_path: str) -> bool:
        """Check if video has an embedded thumbnail.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if video has an embedded thumbnail
        """
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            video_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.PROBE_TIMEOUT
            )

            if process.returncode != 0:
                _LOGGER.debug(
                    "ffprobe returned non-zero exit code: %s", stderr.decode()
                )
                return False

            data = json.loads(stdout.decode())
            streams = data.get("streams", [])
            
            # Check if any stream has disposition attached_pic
            for stream in streams:
                if stream.get("codec_type") == "video":
                    disposition = stream.get("disposition", {})
                    if disposition.get("attached_pic") == 1:
                        return True
            
            return False

        except asyncio.TimeoutError:
            _LOGGER.debug("ffprobe timed out checking for thumbnail after %d seconds", self.PROBE_TIMEOUT)
            return False
        except (json.JSONDecodeError, KeyError, TypeError) as err:
            _LOGGER.debug("Failed to check for thumbnail: %s", err)
            return False

    async def analyze_video_needs_processing(
        self,
        video_path: str,
        normalize_aspect: bool = True,
        generate_thumbnail: bool = True,
        resize_width: int | None = None,
        resize_height: int | None = None,
        target_aspect_ratio: float | None = None,
    ) -> dict[str, Any]:
        """Analyze if video needs processing.
        
        Args:
            video_path: Path to the video file
            normalize_aspect: Whether aspect ratio normalization is requested
            generate_thumbnail: Whether thumbnail generation is requested
            resize_width: Optional target width for resizing
            resize_height: Optional target height for resizing
            target_aspect_ratio: Optional target aspect ratio (default: 16/9)
            
        Returns:
            Dictionary with analysis results
        """
        _LOGGER.info("Analyzing video processing requirements: %s", video_path)

        if target_aspect_ratio is None:
            target_aspect_ratio = 16 / 9

        analysis: dict[str, Any] = {
            "needs_processing": False,
            "reasons": [],
        }

        try:
            # Get video dimensions
            info = await self.get_video_dimensions(video_path)
            current_aspect_ratio = info["aspect_ratio"]
            current_width = info["width"]
            current_height = info["height"]

            # Check if resize is needed
            if resize_width or resize_height:
                # Calculate target dimensions
                video_aspect_ratio = current_width / current_height
                
                if resize_width and resize_height:
                    needs_resize = (
                        current_width != resize_width or 
                        current_height != resize_height
                    )
                elif resize_width:
                    target_height = int(resize_width / video_aspect_ratio)
                    needs_resize = (
                        current_width != resize_width or 
                        current_height != target_height
                    )
                else:  # resize_height only
                    target_width = int(resize_height * video_aspect_ratio)
                    needs_resize = (
                        current_width != target_width or 
                        current_height != resize_height
                    )
                
                if needs_resize:
                    analysis["needs_processing"] = True
                    analysis["reasons"].append("Video dimensions differ from target")

            # Check if aspect ratio normalization is needed
            if normalize_aspect:
                # Check with small tolerance
                if abs(current_aspect_ratio - target_aspect_ratio) >= self.ASPECT_RATIO_TOLERANCE:
                    analysis["needs_processing"] = True
                    analysis["reasons"].append(
                        f"Aspect ratio {current_aspect_ratio:.3f} differs from target "
                        f"{target_aspect_ratio:.3f}"
                    )

            # Check if thumbnail is needed
            if generate_thumbnail:
                has_thumbnail = await self.check_video_has_thumbnail(video_path)
                if not has_thumbnail:
                    analysis["needs_processing"] = True
                    analysis["reasons"].append("Video does not have embedded thumbnail")

            # Add video info to analysis
            analysis["video_info"] = {
                "width": current_width,
                "height": current_height,
                "aspect_ratio": current_aspect_ratio,
            }
            
            # Log analysis results
            if analysis["needs_processing"]:
                _LOGGER.info(
                    "Video needs processing. Reasons: %s", ", ".join(analysis["reasons"])
                )
            else:
                _LOGGER.info("Video already meets all requirements, no processing needed")

        except Exception as err:
            _LOGGER.error("Error analyzing video %s: %s", video_path, err)
            analysis["error"] = str(err)
            # If we can't analyze, assume processing is needed
            analysis["needs_processing"] = True
            analysis["reasons"].append("Failed to analyze video")

        return analysis

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
        _LOGGER.info("Generating thumbnail for video: %s", video_path)

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
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.FFMPEG_OPERATION_TIMEOUT
            )

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to generate thumbnail: %s", stderr.decode()
                )
                return False

            if os.path.exists(thumbnail_path):
                _LOGGER.info("Thumbnail generated successfully at %s", thumbnail_path)
                return True
            
            return False

        except asyncio.TimeoutError:
            _LOGGER.error("Thumbnail generation timed out after %d seconds", self.FFMPEG_OPERATION_TIMEOUT)
            return False
        except Exception as err:
            _LOGGER.error("Error generating thumbnail: %s", err)
            return False

    async def embed_thumbnail(self, video_path: str, output_video_path: str, thumbnail_path: str) -> bool:
        """Embed thumbnail into video file metadata.
        
        Args:
            video_path: Path to the input video file
            output_video_path: Path where the output video will be saved
            thumbnail_path: Path to the thumbnail image
            
        Returns:
            True if thumbnail was embedded successfully
        """
        _LOGGER.info("Embedding thumbnail into video: %s", video_path)

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-i", thumbnail_path,
            "-map", "0",
            "-map", "1",
            "-c", "copy",
            "-disposition:v:1", "attached_pic",
            "-y",
            output_video_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.FFMPEG_OPERATION_TIMEOUT
            )

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to embed thumbnail: %s", stderr.decode()
                )
                # Clean up output file if it exists
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)
                return False

            _LOGGER.info("Thumbnail embedded successfully")
            return True

        except asyncio.TimeoutError:
            _LOGGER.error("Embedding thumbnail timed out after %d seconds", self.FFMPEG_OPERATION_TIMEOUT)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False
        except Exception as err:
            _LOGGER.error("Error embedding thumbnail: %s", err)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False

    async def normalize_aspect_ratio(
        self, video_path: str, output_video_path: str, target_aspect_ratio: float | None = None
    ) -> bool:
        """Normalize video aspect ratio to prevent square or distorted previews.
        
        Args:
            video_path: Path to the input video file
            output_video_path: Path where the output video will be saved
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
        if abs(current_aspect_ratio - target_aspect_ratio) < self.ASPECT_RATIO_TOLERANCE:
            _LOGGER.debug(
                "Video already has correct aspect ratio: %.3f", current_aspect_ratio
            )
            # Copy input to output since no processing is needed
            try:
                shutil.copy2(video_path, output_video_path)
                return True
            except Exception as err:
                _LOGGER.error("Failed to copy video file: %s", err)
                return False

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
            filter_complex = f"pad={width}:{new_height}:0:{pad_top}:black"
        else:
            # Video is taller, add padding left/right
            new_width = int(height * target_aspect_ratio)
            pad_width = new_width - width
            pad_left = pad_width // 2
            filter_complex = f"pad={new_width}:{height}:{pad_left}:0:black"

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", filter_complex,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_video_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.FFMPEG_OPERATION_TIMEOUT
            )

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to normalize aspect ratio: %s", stderr.decode()
                )
                # Clean up output file if it exists
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)
                return False

            _LOGGER.info("Aspect ratio normalized successfully")
            return True

        except asyncio.TimeoutError:
            _LOGGER.error("Aspect ratio normalization timed out after %d seconds", self.FFMPEG_OPERATION_TIMEOUT)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False
        except Exception as err:
            _LOGGER.error("Error normalizing aspect ratio: %s", err)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False

    async def resize_video(
        self, video_path: str, output_video_path: str, target_width: int | None = None, 
        target_height: int | None = None
    ) -> bool:
        """Resize video to specified dimensions.
        
        Args:
            video_path: Path to the input video file
            output_video_path: Path where the output video will be saved
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
        new_width: int
        new_height: int
        if target_width and target_height:
            new_width = target_width
            new_height = target_height
        elif target_width:
            new_width = target_width
            new_height = int(target_width / (current_width / current_height))
        else:  # target_height only
            if target_height is None:
                raise ValueError("Either target_width or target_height must be provided")
            new_height = target_height
            new_width = int(target_height * (current_width / current_height))

        # Check if resize is needed
        if new_width == current_width and new_height == current_height:
            _LOGGER.debug("Video already has target dimensions")
            # Copy input to output since no processing is needed
            try:
                shutil.copy2(video_path, output_video_path)
                return True
            except Exception as err:
                _LOGGER.error("Failed to copy video file: %s", err)
                return False

        _LOGGER.info(
            "Resizing video from %dx%d to %dx%d",
            current_width, current_height, new_width, new_height
        )

        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-vf", f"scale={new_width}:{new_height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "copy",
            "-y",
            output_video_path,
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.FFMPEG_OPERATION_TIMEOUT
            )

            if process.returncode != 0:
                _LOGGER.error(
                    "Failed to resize video: %s", stderr.decode()
                )
                # Clean up output file if it exists
                if os.path.exists(output_video_path):
                    os.remove(output_video_path)
                return False

            _LOGGER.info("Video resized successfully")
            return True

        except asyncio.TimeoutError:
            _LOGGER.error("Video resizing timed out after %d seconds", self.FFMPEG_OPERATION_TIMEOUT)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False
        except Exception as err:
            _LOGGER.error("Error resizing video: %s", err)
            # Clean up output file if it exists
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                except Exception:
                    pass
            return False

    async def process_video(
        self,
        video_path: str,
        output_path: str | None = None,
        output_name: str | None = None,
        overwrite: bool = False,
        normalize_aspect: bool = True,
        generate_thumbnail: bool = True,
        resize_width: int | None = None,
        resize_height: int | None = None,
        target_aspect_ratio: float | None = None,
    ) -> dict[str, Any]:
        """Process video with all requested operations.
        
        Args:
            video_path: Path to the video file
            output_path: Optional output directory path (defaults to same directory as input)
            output_name: Optional output filename (defaults to same name as input)
            overwrite: Whether to overwrite the original file
            normalize_aspect: Whether to normalize aspect ratio
            generate_thumbnail: Whether to generate and embed thumbnail
            resize_width: Optional target width for resizing
            resize_height: Optional target height for resizing
            target_aspect_ratio: Optional target aspect ratio (default: 16/9)
            
        Returns:
            Dictionary with processing results
        """
        results: dict[str, Any] = {
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

            # Analyze if video needs processing
            analysis = await self.analyze_video_needs_processing(
                video_path,
                normalize_aspect,
                generate_thumbnail,
                resize_width,
                resize_height,
                target_aspect_ratio,
            )
            
            results["analysis"] = analysis

            # If video doesn't need processing, skip and return success
            if not analysis["needs_processing"]:
                _LOGGER.info(
                    "Video does not need processing: %s", video_path
                )
                results["success"] = True
                results["skipped"] = True
                results["skip_reason"] = "Video already meets all requirements"
                results["output_path"] = video_path
                results["final_dimensions"] = results["original_dimensions"]
                return results

            # Determine output file path
            if overwrite:
                # When overwriting, we'll work with temp file and replace at the end
                final_output_path = video_path
            else:
                # Determine the output path and name
                video_dir = os.path.dirname(video_path)
                video_basename = os.path.basename(video_path)
                
                if output_path:
                    # Use specified output directory
                    os.makedirs(output_path, exist_ok=True)
                    target_dir = output_path
                else:
                    # Use same directory as input
                    target_dir = video_dir
                
                if output_name:
                    # Use specified output name
                    final_output_path = os.path.join(target_dir, output_name)
                else:
                    # Use same name as input
                    final_output_path = os.path.join(target_dir, video_basename)
            
            # Working file starts as the input
            current_video = video_path
            temp_files = []
            
            # Step 1: Resize if requested (do this before aspect ratio normalization)
            if resize_width or resize_height:
                # Preserve original extension for ffmpeg format detection
                base_path, ext = os.path.splitext(video_path)
                temp_output = f"{base_path}.resize.tmp{ext}"
                temp_files.append(temp_output)
                resize_success = await self.resize_video(
                    current_video, temp_output, resize_width, resize_height
                )
                results["operations"]["resize"] = resize_success
                if resize_success:
                    current_video = temp_output
                else:
                    _LOGGER.warning("Resize operation failed, continuing with other operations")

            # Step 2: Normalize aspect ratio
            if normalize_aspect:
                # Preserve original extension for ffmpeg format detection
                base_path, ext = os.path.splitext(video_path)
                temp_output = f"{base_path}.normalize.tmp{ext}"
                temp_files.append(temp_output)
                normalize_success = await self.normalize_aspect_ratio(
                    current_video, temp_output, target_aspect_ratio
                )
                results["operations"]["normalize_aspect"] = normalize_success
                if normalize_success:
                    current_video = temp_output
                else:
                    _LOGGER.warning("Aspect ratio normalization failed, continuing with other operations")

            # Step 3: Generate and embed thumbnail
            if generate_thumbnail:
                # Generate thumbnail in the same directory as the video
                video_dir = os.path.dirname(video_path)
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                thumbnail_path = os.path.join(video_dir, f"{video_name}_thumb.jpg")
                temp_files.append(thumbnail_path)

                thumbnail_success = await self.generate_thumbnail(
                    current_video, thumbnail_path
                )
                results["operations"]["generate_thumbnail"] = thumbnail_success

                if thumbnail_success:
                    # Preserve original extension for ffmpeg format detection
                    base_path, ext = os.path.splitext(video_path)
                    temp_output = f"{base_path}.thumbnail.tmp{ext}"
                    temp_files.append(temp_output)
                    embed_success = await self.embed_thumbnail(
                        current_video, temp_output, thumbnail_path
                    )
                    results["operations"]["embed_thumbnail"] = embed_success
                    if embed_success:
                        current_video = temp_output
                else:
                    results["operations"]["embed_thumbnail"] = False

            # Copy/move the final result to the output path
            if current_video != video_path:
                # We have a processed video
                if overwrite:
                    # Replace original (moves the file, so it no longer exists as temp)
                    os.replace(current_video, final_output_path)
                else:
                    # Copy to output path (temp file still exists and needs cleanup)
                    shutil.copy2(current_video, final_output_path)
                    
                results["output_path"] = final_output_path
            elif not overwrite and final_output_path != video_path:
                # No processing was done but user wants a copy
                shutil.copy2(video_path, final_output_path)
                results["output_path"] = final_output_path
            else:
                # No processing and overwrite mode
                results["output_path"] = video_path

            # Store temp files list in results for cleanup after sensor state update
            results["temp_files"] = temp_files

            # Get final video information
            final_info = await self.get_video_dimensions(results["output_path"])
            results["final_dimensions"] = {
                "width": final_info["width"],
                "height": final_info["height"],
                "aspect_ratio": final_info["aspect_ratio"],
            }

            # Success if at least one operation succeeded, or no operations were requested (simple copy)
            results["success"] = (
                any(results["operations"].values()) if results["operations"] 
                else "output_path" in results
            )

        except Exception as err:
            _LOGGER.error("Error processing video %s: %s", video_path, err)
            results["error"] = str(err)

        return results
