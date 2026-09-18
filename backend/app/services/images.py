from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 32_000_000


def sanitize_image(data: bytes, content_type: str | None) -> bytes:
    if content_type not in {"image/jpeg", "image/png"}:
        raise ValueError("Only JPEG and PNG images are supported")
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Image must be between 1 byte and 20 MB")
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in {"JPEG", "PNG"} or probe.width * probe.height > MAX_PIXELS:
                raise ValueError("Unsupported image format or dimensions")
            if (probe.format == "JPEG" and content_type != "image/jpeg") or (probe.format == "PNG" and content_type != "image/png"):
                raise ValueError("Image MIME type does not match its contents")
            probe.verify()
        with Image.open(BytesIO(data)) as source:
            if source.width < 64 or source.height < 64:
                raise ValueError("Image dimensions are too small")
            image = ImageOps.exif_transpose(source).convert("RGB")
            output = BytesIO()
            if content_type == "image/png":
                image.save(output, format="PNG", optimize=True)
            else:
                image.save(output, format="JPEG", quality=95, subsampling=0)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid image data") from exc
