# backend/providers/music_replicate.py
import os
from fastapi import HTTPException
import httpx

_REPLICATE_AVAILABLE = True
try:
    import replicate
except Exception:
    _REPLICATE_AVAILABLE = False

from utils.logging import setup_logger
from utils.storage import AUD_DIR
log = setup_logger()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "elevenlabs/music").strip()
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION", "").strip()


def _ensure_replicate_ready():
    if not REPLICATE_API_TOKEN:
        raise HTTPException(500, "Missing REPLICATE_API_TOKEN in .env")
    if not _REPLICATE_AVAILABLE:
        raise HTTPException(500, "Replicate SDK not installed. Install with: pip install replicate")
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN


async def generate_elevenlabs_music(
    prompt: str, duration_seconds: int, slug: str, client: httpx.AsyncClient
) -> str:
    """
    Runs ElevenLabs Music via Replicate and downloads resulting mp3.
    Returns local mp3 path.
    """
    _ensure_replicate_ready()

    dur = max(1, min(int(duration_seconds), 300))
    music_length_ms = dur * 1000
    model_ref = REPLICATE_MODEL if not REPLICATE_MODEL_VERSION else f"{REPLICATE_MODEL}:{REPLICATE_MODEL_VERSION}"

    log.info("[Replicate] %s — %ss, instrumental=True, mp3", model_ref, dur)

    try:
        output = replicate.run(
            model_ref,
            input={
                "prompt": prompt,
                "output_format": "mp3_high_quality",
                "music_length_ms": music_length_ms,
                "force_instrumental": True,
            },
        )
    except Exception as e:
        log.exception("Replicate run failed")
        raise HTTPException(502, f"Replicate SDK error: {e}")

    # Normalize the returned output into a URL we can download
    try:
        if isinstance(output, str):
            url = output
        elif isinstance(output, list) and output and isinstance(output[0], str):
            url = output[0]
        elif hasattr(output, "url"):
            url = output.url() if callable(output.url) else output.url
        else:
            url = None

        if not url or not str(url).startswith("http"):
            raise HTTPException(502, f"ElevenLabs output missing valid URL: {repr(url)}")

        mp3_path = os.path.join(AUD_DIR, f"{slug}.mp3")

        # If replicate returned a file-like output with read(), prefer that
        if hasattr(output, "read"):
            with open(mp3_path, "wb") as f:
                f.write(output.read())
            return mp3_path

        # Download via httpx
        r = await client.get(url)
        r.raise_for_status()
        with open(mp3_path, "wb") as f:
            f.write(r.content)
        return mp3_path

    except HTTPException:
        raise
    except Exception as e:
        log.exception("Processing ElevenLabs output failed")
        raise HTTPException(500, f"Failed to process ElevenLabs output: {e}")
