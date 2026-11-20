"""
Unit tests for live stream detection, metadata probing, and recording capture.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.media.live_stream import (
    DEFAULT_LIVE_CAPTURE_SECONDS,
    LiveStreamError,
    LiveStreamOfflineError,
    capture_live_stream,
    is_channel_live_url,
    probe_live_stream_info,
)
from src.stream_source import detect_stream_source, fetch_stream_info


def test_is_channel_live_url():
    # Twitch live channels
    assert is_channel_live_url("https://www.twitch.tv/ninja") is True
    assert is_channel_live_url("https://twitch.tv/shroud") is True
    assert is_channel_live_url("https://m.twitch.tv/streamer") is True
    # Twitch VOD or clips are not live channels
    assert is_channel_live_url("https://www.twitch.tv/videos/123456") is False
    assert is_channel_live_url("https://www.twitch.tv/streamer/clip/abc") is False
    assert is_channel_live_url("https://www.twitch.tv/directory") is False

    # Kick live channels
    assert is_channel_live_url("https://kick.com/xqc") is True
    assert is_channel_live_url("https://kick.com/creator") is True
    # Kick VOD or clips are not live channels
    assert is_channel_live_url("https://kick.com/creator/videos/12345678-1234-1234-1234-123456789abc") is False
    assert is_channel_live_url("https://kick.com/creator/clips/clip_123") is False
    assert is_channel_live_url("https://kick.com/categories") is False

    # YouTube live link
    assert is_channel_live_url("https://www.youtube.com/live/abcdefghijk") is True
    assert is_channel_live_url("https://www.youtube.com/watch?v=abcdefghijk") is False


def test_detect_stream_source_live():
    # Twitch channel returns live kind
    source, kind, stream_id = detect_stream_source("https://www.twitch.tv/ninja")
    assert source == "twitch"
    assert kind == "live"
    assert stream_id == "ninja"

    # Kick channel returns live kind
    source, kind, stream_id = detect_stream_source("https://kick.com/xqc")
    assert source == "kick"
    assert kind == "live"
    assert stream_id == "xqc"


@patch("yt_dlp.YoutubeDL")
def test_probe_live_stream_info_active(mock_ydl_cls):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "id": "ninja",
        "title": "Fortnite Tournament LIVE",
        "uploader": "ninja",
        "is_live": True,
        "url": "https://video.twitch.tv/live.m3u8",
    }
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    info = probe_live_stream_info("https://www.twitch.tv/ninja")
    assert info["is_live"] is True
    assert info["title"] == "Fortnite Tournament LIVE"
    assert info["url"] == "https://video.twitch.tv/live.m3u8"


@patch("yt_dlp.YoutubeDL")
def test_probe_live_stream_info_offline(mock_ydl_cls):
    mock_ydl = MagicMock()
    # Offline channel has no live stream active
    mock_ydl.extract_info.return_value = {
        "id": "ninja",
        "title": "ninja",
        "is_live": False,
        "live_status": "not_live",
        "duration": None,
    }
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    with pytest.raises(LiveStreamOfflineError):
        probe_live_stream_info("https://www.twitch.tv/ninja")


@patch("src.media.live_stream.probe_live_stream_info")
def test_fetch_stream_info_live(mock_probe):
    mock_probe.return_value = {
        "id": "ninja",
        "title": "Twitch Championship Live",
        "is_live": True,
        "url": "https://video.twitch.tv/live.m3u8",
    }
    result = fetch_stream_info("https://www.twitch.tv/ninja")
    assert result["is_live"] is True
    assert result["id"] == "ninja"
    assert result["title"] == "Twitch Championship Live"
    assert result["duration"] == float(DEFAULT_LIVE_CAPTURE_SECONDS)


@patch("src.media.live_stream.ffprobe_duration")
@patch("src.media.live_stream.run_ffmpeg_command")
@patch("yt_dlp.YoutubeDL")
def test_capture_live_stream_success(mock_ydl_cls, mock_ffmpeg, mock_duration, tmp_path):
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "url": "https://example.com/live/playlist.m3u8",
    }
    mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

    output_path = tmp_path / "output.mp4"
    mock_duration.return_value = 900.0

    # Side-effect: simulate ffmpeg creating the temp recording file
    def ffmpeg_side_effect(cmd, timeout=None):
        target_arg = Path(cmd[-1])
        target_arg.touch()
        # write dummy bytes
        target_arg.write_bytes(b"dummy mp4 video bytes")

    mock_ffmpeg.side_effect = ffmpeg_side_effect

    res = capture_live_stream(
        "https://www.twitch.tv/ninja",
        output_path,
        duration_seconds=900,
    )
    assert res == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert mock_ffmpeg.called


@pytest.mark.asyncio
async def test_preflight_youtube_live_source():
    from src.api.routes.tasks import _preflight_youtube_source
    with patch("src.api.routes.tasks.async_get_youtube_video_info") as mock_info:
        # YouTube live metadata returns duration 0 and is_live True
        mock_info.return_value = {
            "id": "live123",
            "title": "Breaking News LIVE",
            "is_live": True,
            "duration": 0,
        }
        metadata = await _preflight_youtube_source(
            "https://www.youtube.com/live/live123",
            duration_limit=5400,
            is_live=True,
            live_duration_seconds=1200,
        )
        assert metadata["is_live"] is True
        assert metadata["duration"] == 1200.0


@pytest.mark.asyncio
async def test_preflight_stream_live_source():
    from src.api.routes.tasks import _preflight_stream_source
    with patch("src.api.routes.tasks.fetch_stream_info") as mock_stream_info:
        mock_stream_info.return_value = {
            "id": "streamer",
            "title": "Streamer Live",
            "is_live": True,
            "duration": 900.0,
            "provider": "direct",
        }
        metadata = await _preflight_stream_source(
            "https://www.twitch.tv/streamer",
            source="twitch",
            duration_limit=5400,
            is_live=True,
            live_duration_seconds=1800,
        )
        assert metadata["is_live"] is True
        assert metadata["duration"] == 1800.0
