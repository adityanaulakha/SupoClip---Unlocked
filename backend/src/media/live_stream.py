"""
Live stream capture and processing helpers for YouTube Live, Twitch, and Kick streams.
Uses yt-dlp to resolve live stream manifests and ffmpeg to record bounded windows.
"""

from __future__ import annotations

import logging
import math
import os
import re
from pathlib import Path
import subprocess
import time
from typing import Any, Awaitable, Callable, Dict, Optional
from urllib.parse import urlparse

import yt_dlp

from ..config import get_config
from .ffmpeg import ffprobe_duration, ffprobe_has_audio, run_ffmpeg_command

logger = logging.getLogger(__name__)

DEFAULT_LIVE_CAPTURE_SECONDS = 900  # 15 minutes default
MIN_LIVE_CAPTURE_SECONDS = 60       # 1 minute minimum
MAX_LIVE_CAPTURE_SECONDS = 7200     # 2 hours maximum


class LiveStreamError(RuntimeError):
    """User-facing live stream capture error."""


class LiveStreamOfflineError(LiveStreamError):
    """The requested channel or broadcast is currently offline."""


def is_channel_live_url(url: str) -> bool:
    """Check if the URL pattern points to a live stream channel rather than a VOD."""
    try:
        parsed = urlparse(str(url).strip())
    except Exception:
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    path = parsed.path.rstrip("/") or "/"
    
    # Twitch live channel: twitch.tv/<channel>
    if host in {"twitch.tv", "m.twitch.tv", "go.twitch.tv"}:
        if path != "/" and re.fullmatch(r"^/[A-Za-z0-9_]+$", path):
            if path.lower() not in {"/videos", "/directory", "/search", "/settings"}:
                return True
                
    # Kick live channel: kick.com/<channel>
    if host in {"kick.com", "www.kick.com"}:
        if path != "/" and re.fullmatch(r"^/[A-Za-z0-9_-]+$", path):
            if path.lower() not in {"/video", "/videos", "/categories", "/browse", "/search"}:
                return True

    # YouTube live link: youtube.com/live/<id>
    if "youtube.com" in host or "youtu.be" in host:
        if path.startswith("/live/"):
            return True

    return False


def probe_live_stream_info(url: str, timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    Probe a live stream URL to check if it is active and extract metadata.
    Raises LiveStreamOfflineError if the stream is offline or not found.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": timeout_seconds,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise LiveStreamOfflineError("Stream information could not be retrieved.")

            live_status = str(info.get("live_status") or "").lower()
            is_live = bool(info.get("is_live")) or (live_status in {"is_live", "post_live"})
            if not is_live and live_status not in {"not_live", "is_offline", "was_live"} and info.get("duration") is None and is_channel_live_url(url):
                if info.get("formats") or info.get("url"):
                    is_live = True

            if not is_live:
                raise LiveStreamOfflineError("This channel is currently offline. Please wait until they go live.")

            return {
                "id": info.get("id"),
                "title": info.get("title") or "Live Stream",
                "uploader": info.get("uploader") or info.get("channel") or "Live Streamer",
                "is_live": True,
                "url": info.get("url"),
                "thumbnail": info.get("thumbnail"),
            }
    except LiveStreamOfflineError:
        raise
    except Exception as exc:
        msg = str(exc)
        if any(term in msg.lower() for term in ["offline", "not live", "is offline", "no live stream"]):
            raise LiveStreamOfflineError("This live stream is currently offline.") from exc
        logger.warning("Error probing live stream %s: %s", url, exc)
        raise LiveStreamError(f"Could not connect to live stream: {exc}") from exc


def capture_live_stream(
    url: str,
    output_path: Path,
    duration_seconds: int = DEFAULT_LIVE_CAPTURE_SECONDS,
    progress_callback: Optional[Callable[[int, str, str], Awaitable[None]]] = None,
    should_cancel: Optional[Callable[[], Awaitable[bool]]] = None,
) -> Path:
    """
    Capture an active live stream for the specified duration and write to output_path.
    Uses ffmpeg to record the bounded window directly from the stream feed.
    """
    duration_seconds = max(MIN_LIVE_CAPTURE_SECONDS, min(MAX_LIVE_CAPTURE_SECONDS, int(duration_seconds)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_target = output_path.with_suffix(f".recording_{int(time.time())}.mp4")

    logger.info("Starting live stream capture: %s -> %s (%d seconds)", url, temp_target, duration_seconds)

    # Strategy 1: Extract direct stream URL (HLS / m3u8) via yt-dlp and capture with ffmpeg
    stream_manifest_url: Optional[str] = None
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                stream_manifest_url = info.get("url")
    except Exception as exc:
        logger.warning("Direct stream extraction failed for %s, falling back to yt-dlp capture: %s", url, exc)

    if stream_manifest_url:
        cmd = [
            "ffmpeg",
            "-y",
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-i", stream_manifest_url,
            "-t", str(duration_seconds),
            "-c:v", "copy",
            "-c:a", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            str(temp_target),
        ]
        try:
            # Allow duration + 60s grace period for ffmpeg to finish
            run_ffmpeg_command(cmd, timeout=duration_seconds + 60)
        except Exception as exc:
            logger.warning("Stream copy failed: %s; retrying with re-encode fallback", exc)
            # Transcode fallback if stream copy has bitstream incompatibility
            cmd_transcode = [
                "ffmpeg",
                "-y",
                "-i", stream_manifest_url,
                "-t", str(duration_seconds),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(temp_target),
            ]
            try:
                run_ffmpeg_command(cmd_transcode, timeout=duration_seconds + 90)
            except Exception as inner_exc:
                logger.error("FFmpeg transcode stream capture failed: %s", inner_exc)
                temp_target.unlink(missing_ok=True)

    # Strategy 2: If strategy 1 didn't produce a valid recording, run yt-dlp directly with ffmpeg duration
    if not temp_target.exists() or temp_target.stat().st_size == 0:
        logger.info("Capturing via yt-dlp with external downloader args...")
        ydl_download_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": str(temp_target),
            "external_downloader": "ffmpeg",
            "external_downloader_args": {"ffmpeg_i": ["-t", str(duration_seconds)]},
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_download_opts) as ydl:
                ydl.download([url])
        except Exception as exc:
            logger.error("yt-dlp live capture failed: %s", exc)
            temp_target.unlink(missing_ok=True)
            raise LiveStreamError(f"Failed to capture live stream: {exc}") from exc

    # Locate actual recorded file if yt-dlp chose a different extension or output template
    if not temp_target.exists() or temp_target.stat().st_size == 0:
        candidates = list(temp_target.parent.glob(f"{temp_target.stem}.*"))
        for cand in candidates:
            if cand.is_file() and cand.stat().st_size > 0:
                temp_target = cand
                break

    if not temp_target.exists() or temp_target.stat().st_size == 0:
        raise LiveStreamError("Live stream capture produced an empty video file.")

    # Remux to standard MP4 with faststart so the rest of the clipping pipeline and browsers can read it smoothly
    remuxed_target = output_path.with_suffix(f".remuxed_{int(time.time())}.mp4")
    cmd_remux = [
        "ffmpeg",
        "-y",
        "-i", str(temp_target),
        "-c", "copy",
        "-movflags", "+faststart",
        str(remuxed_target),
    ]
    try:
        run_ffmpeg_command(cmd_remux, timeout=120)
        temp_target.unlink(missing_ok=True)
        temp_target = remuxed_target
    except Exception as exc:
        logger.warning("Fast remux failed (%s), keeping recorded output as-is", exc)
        remuxed_target.unlink(missing_ok=True)

    if not temp_target.exists() or temp_target.stat().st_size == 0:
        raise LiveStreamError("Live stream capture produced an empty video file.")

    # Validate recorded duration
    recorded_duration = ffprobe_duration(temp_target)
    if recorded_duration <= 0:
        temp_target.unlink(missing_ok=True)
        raise LiveStreamError("Captured live stream has invalid duration.")

    # Move to final output path
    temp_target.replace(output_path)
    logger.info("Live stream capture complete: %s (duration: %.1fs)", output_path, recorded_duration)
    return output_path
