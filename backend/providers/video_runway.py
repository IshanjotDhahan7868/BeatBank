# backend/providers/video_runway.py
import os
import asyncio
import httpx
from typing import Optional
from fastapi import HTTPException

from utils.logging import setup_logger
from utils.storage import VID_DIR, safe_slug
from moviepy.editor import VideoFileClip, AudioFileClip

log = setup_logger()

RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "").strip()
# Tweakable defaults (override in .env if you like)
RUNWAY_API_BASE = os.getenv("RUNWAY_API_BASE", "https://api.runwayml.com/v1")
RUNWAY_MODEL = os.getenv("RUNWAY_MODEL", "gen3-alpha")           # adjust if needed
RUNWAY_POLL_SECONDS = int(os.getenv("RUNWAY_POLL_SECONDS", "3"))  # poll interval

HEADERS = {"Authorization": f"Bearer {RUNWAY_API_KEY}", "Content-Type": "application/json"}


def _assert_ready():
    if not RUNWAY_API_KEY:
        raise HTTPException(500, "Missing RUNWAY_API_KEY in .env")


async def start_runway_job(prompt: str, duration: int, client: httpx.AsyncClient) -> str:
    """
    Kicks off an AI video generation job and returns a job_id.
    NOTE: Endpoint shape varies by account/plan. Adjust 'endpoint' or payload fields if needed.
    """
    _assert_ready()
    endpoint = f"{RUNWAY_API_BASE}/generations"   # common Runway pattern; update if your account differs

    payload = {
        "model": RUNWAY_MODEL,
        "prompt": prompt,
        # Some Runway variants accept seconds; others accept frames. Duration handling may vary.
        "duration": max(2, min(duration, 30)),  # keep short for MVP; adjust as your plan allows
        # You can add style_preset, seed, ratio, motion settings, etc. when you refine
    }

    try:
        r = await client.post(endpoint, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()
        # Normalize: some APIs return {id: "..."}; others nest it.
        job_id = data.get("id") or data.get("job_id") or data.get("generation_id")
        if not job_id:
            raise HTTPException(502, f"Runway response missing job id: {data}")
        log.info(f"[Runway] started job {job_id}")
        return job_id
    except httpx.HTTPError as e:
        log.exception("Runway start failed")
        raise HTTPException(502, f"Runway start error: {e}")


async def poll_runway_job(job_id: str, client: httpx.AsyncClient) -> str:
    """
    Polls until the job finishes and returns a downloadable video URL.
    """
    _assert_ready()
    status_endpoint = f"{RUNWAY_API_BASE}/generations/{job_id}"

    while True:
        try:
            r = await client.get(status_endpoint, headers=HEADERS)
            r.raise_for_status()
            data = r.json()

            status = (data.get("status") or data.get("state") or "").lower()
            # Normalize a few common shapes
            # expected final: data["output"]["video"] OR data["output_url"]
            output_url = (
                (data.get("output") or {}).get("video")
                if isinstance(data.get("output"), dict)
                else data.get("output_url")
            )

            if status in ("succeeded", "completed", "finished"):
                if not output_url:
                    raise HTTPException(502, f"Runway finished but no output url: {data}")
                log.info(f"[Runway] job {job_id} finished")
                return output_url

            if status in ("failed", "error", "canceled"):
                raise HTTPException(502, f"Runway job failed: {data}")

            await asyncio.sleep(RUNWAY_POLL_SECONDS)
        except httpx.HTTPError as e:
            log.warning(f"[Runway] poll error: {e}; retrying in {RUNWAY_POLL_SECONDS}s")
            await asyncio.sleep(RUNWAY_POLL_SECONDS)


async def download_runway_video(url: str, out_path: str, client: httpx.AsyncClient) -> str:
    """
    Downloads the AI video mp4 to out_path.
    """
    try:
        r = await client.get(url)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
        return out_path
    except httpx.HTTPError as e:
        log.exception("Runway download failed")
        raise HTTPException(502, f"Runway download error: {e}")


def overlay_audio_on_video(video_path: str, audio_path: str, out_path: str, fps: int = 30) -> str:
    """
    Overlays (replaces) the video's audio with your generated beat, writes to out_path.
    """
    try:
        v = VideoFileClip(video_path)
        a = AudioFileClip(audio_path)
        # Trim/loop logic for MVP: cut to the shorter of the two
        dur = min(v.duration, a.duration)
        v = v.subclip(0, dur).set_audio(a.subclip(0, dur))
        v.write_videofile(out_path, fps=fps, codec="libx264", audio_codec="aac")
        return out_path
    except Exception as e:
        log.exception("Overlay audio on video failed")
        raise HTTPException(500, f"Overlay error: {e}")


async def create_ai_video_with_audio(
    prompt: str,
    duration: int,
    audio_path: Optional[str],
    title_hint: str,
    client: httpx.AsyncClient,
) -> dict:
    """
    High-level helper: start → poll → download → (optional) overlay audio → return paths.
    """
    slug = safe_slug(title_hint or prompt)
    temp_ai_path = os.path.join(VID_DIR, f"{slug}_ai_raw.mp4")
    final_path = os.path.join(VID_DIR, f"{slug}_ai_final.mp4")

    job_id = await start_runway_job(prompt, duration, client)
    video_url = await poll_runway_job(job_id, client)
    await download_runway_video(video_url, temp_ai_path, client)

    if audio_path:
        out = overlay_audio_on_video(temp_ai_path, audio_path, final_path)
        return {"ai_video_raw_path": temp_ai_path, "ai_video_final_path": out, "cdn_url": video_url}

    # No audio overlay requested
    return {"ai_video_raw_path": temp_ai_path, "ai_video_final_path": temp_ai_path, "cdn_url": video_url}
