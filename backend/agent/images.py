"""Turns a screenshot or product photo into an image block for the model."""

from __future__ import annotations

import base64
from pathlib import Path

# Kept under the per-image limits of the common providers.
MAX_IMAGE_BYTES = 3_500_000


class ImageError(ValueError):
    """The input is not a usable image. The message is safe to display."""


def _mime_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def read_image(source: bytes | Path) -> tuple[bytes, str]:
    """The image bytes and their MIME type, taken from the bytes, not the file name."""
    if isinstance(source, Path):
        try:
            data = source.read_bytes()
        except OSError:
            raise ImageError("The image file could not be read.") from None
    else:
        data = bytes(source)

    if not data:
        raise ImageError("The image is empty.")
    mime_type = _mime_type(data)
    if mime_type is None:
        raise ImageError("The image must be a PNG, JPEG or WebP file.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageError("The image is too large. Use a screenshot under 3.5 MB.")
    return data, mime_type


def image_block(data: bytes, mime_type: str) -> dict:
    """A LangChain standard image content block."""
    return {"type": "image", "base64": base64.b64encode(data).decode("ascii"), "mime_type": mime_type}
