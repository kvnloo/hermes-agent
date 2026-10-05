"""Native attachment method selection for cron delivery."""

from pathlib import Path


# Audio routing is centralized in gateway.platforms.base.should_send_media_as_audio().
_VIDEO_EXTS = frozenset({'.mp4', '.mov', '.avi', '.mkv', '.webm', '.3gp'})
_IMAGE_EXTS = frozenset({'.jpg', '.jpeg', '.png', '.webp', '.gif'})


def media_send_route(route_platform, media_path, _is_voice):
    """Choose the native sender and preserve the caller's voice-bubble intent."""
    from gateway.platforms.base import should_send_media_as_audio

    ext = Path(media_path).suffix.lower()
    if should_send_media_as_audio(route_platform, ext, is_voice=_is_voice):
        method, path_kw = "send_voice", "audio_path"
    elif ext in _VIDEO_EXTS:
        method, path_kw = "send_video", "video_path"
    elif ext in _IMAGE_EXTS:
        method, path_kw = "send_image_file", "image_path"
    else:
        method, path_kw = "send_document", "file_path"
    # The voice sender decides bubble vs music-file from ``is_voice`` (Telegram
    # transcodes non-Opus only when it is set), matching the gateway dispatch
    # in BasePlatformAdapter._send_one.
    extra = {"is_voice": _is_voice} if method == "send_voice" else {}
    return method, path_kw, extra
