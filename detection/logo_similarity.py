import logging
from io import BytesIO
from urllib.parse import urlsplit

import requests
from PIL import Image, UnidentifiedImageError


logger = logging.getLogger(__name__)
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_TIMEOUT = (3.05, 6)


def _open_image(image):
    if hasattr(image, "read"):
        image.seek(0)
        return Image.open(image)
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, (bytes, bytearray)):
        return Image.open(BytesIO(image))
    return Image.open(image)


def logo_similarity(candidate_image, official_image):
    """Compare two image sources using 64-bit difference hashes; return 0.0–1.0."""
    if not candidate_image or not official_image:
        return None
    with _open_image(candidate_image) as candidate, _open_image(official_image) as official:
        candidate_hash = _difference_hash(candidate)
        official_hash = _difference_hash(official)
    distance = (candidate_hash ^ official_hash).bit_count()
    return 1.0 - distance / 64


def _difference_hash(image):
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("Image is too large to compare safely.")
    grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(grayscale.getdata())
    result = 0
    for row in range(8):
        for column in range(8):
            left = pixels[row * 9 + column]
            right = pixels[row * 9 + column + 1]
            result = (result << 1) | int(left > right)
    return result


def remote_app_logo_similarity(artwork_url, official_logo):
    """Compare Apple-hosted app artwork safely; never fetch arbitrary candidate URLs."""
    if not artwork_url or not official_logo:
        return None
    parsed = urlsplit(artwork_url)
    hostname = (parsed.hostname or "").casefold()
    trusted_artwork_hosts = (
        hostname == "mzstatic.com"
        or hostname.endswith(".mzstatic.com")
        or hostname == "play-lh.googleusercontent.com"
    )
    if parsed.scheme != "https" or not trusted_artwork_hosts:
        logger.info("Skipped artwork URL outside the trusted Apple CDN.")
        return None
    try:
        response = requests.get(
            artwork_url,
            timeout=IMAGE_TIMEOUT,
            stream=True,
            allow_redirects=False,
            headers={"User-Agent": "DigitalRiskProtectionPrototype/1.0"},
        )
        with response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            content_length = response.headers.get("Content-Length")
            if not content_type.startswith("image/"):
                logger.warning("Skipped app artwork with non-image content type.")
                return None
            if content_length and int(content_length) > MAX_IMAGE_BYTES:
                logger.warning("Skipped app artwork larger than the configured size limit.")
                return None
            content = bytearray()
            for chunk in response.iter_content(16 * 1024):
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    logger.warning("Skipped app artwork larger than the configured size limit.")
                    return None
        return logo_similarity(bytes(content), official_logo)
    except requests.RequestException as exc:
        logger.warning("Could not retrieve app artwork: %s", exc.__class__.__name__)
        return None
    except (ValueError, UnidentifiedImageError, OSError) as exc:
        logger.warning("Could not compare app artwork: %s", exc.__class__.__name__)
        return None
