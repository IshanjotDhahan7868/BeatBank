#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatBank API — FINAL (main_final.py)
Date: 2025-11-04

🎵 Music provider: ElevenLabs via Replicate (elevenlabs/music)
- Uses Replicate's Python SDK (preferred) with your REPLICATE_API_TOKEN
- No hardcoded version needed; if REPLICATE_MODEL_VERSION is set, we'll use it
- input: prompt (text), duration (seconds) → converted to music_length_ms
- force_instrumental=True (as requested)
- output_format="mp3" (as requested)
- Writes downloaded audio to artifacts/audio/<slug>.mp3

Other features kept:
- OpenAI metadata (gpt-4o-mini)
- OpenAI cover art (gpt-image-1)
- Simple MoviePy visualizer
- Supabase insertions

ENV (.env) — required
---------------------
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
REPLICATE_API_TOKEN= r8_...

Optional (we provide defaults):
REPLICATE_MODEL=elevenlabs/music
# If you want to pin a specific version, set it:
REPLICATE_MODEL_VERSION=<hash>

Run:
-----
pip install fastapi uvicorn httpx python-dotenv supabase moviepy openai replicate aiofiles
uvicorn main_final:app --reload --port 8000
"""

import os
import re
import io
import json
import base64
import uuid
import asyncio
import logging
import librosa
from typing import Optional, Literal, List, Union

import aiofiles
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# Media
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, vfx

# OpenAI SDK
from openai import OpenAI

# Replicate SDK (preferred path for ElevenLabs)
_REPLICATE_AVAILABLE = True
try:
    import replicate
except Exception:
    _REPLICATE_AVAILABLE = False

# Optional local MusicGen (fallback)
_MUSICGEN_AVAILABLE = True
try:
    import torch  # noqa: F401
    import numpy as np  # noqa: F401
    from scipy.io.wavfile import write as wavwrite  # noqa: F401
    from audiocraft.models import MusicGen  # noqa: F401
except Exception:
    _MUSICGEN_AVAILABLE = False

# ----------------------------
# Setup
# ----------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("beatbank")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in .env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Replicate
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "elevenlabs/music").strip()
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION", "").strip()

# Storage
ART_DIR = "artifacts"
IMG_DIR = os.path.join(ART_DIR, "images")
VID_DIR = os.path.join(ART_DIR, "videos")
AUD_DIR = os.path.join(ART_DIR, "audio")
for d in (ART_DIR, IMG_DIR, VID_DIR, AUD_DIR):
    os.makedirs(d, exist_ok=True)

# ----------------------------
# App
# ----------------------------
app = FastAPI(title="BeatBank API (Final)", version="2025.11.04")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

_http: Optional[httpx.AsyncClient] = None

@app.on_event("startup")
async def _startup():
    global _http
    _http = httpx.AsyncClient(timeout=600)
    model_label = REPLICATE_MODEL if not REPLICATE_MODEL_VERSION else f"{REPLICATE_MODEL}:{REPLICATE_MODEL_VERSION[:8]}"
    log.info("BeatBank API (Final) online — using %s", model_label)

@app.on_event("shutdown")
async def _shutdown():
    global _http
    if _http:
        await _http.aclose()
        log.info("HTTP client closed.")

def ensure_http() -> httpx.AsyncClient:
    if not _http:
        raise RuntimeError("HTTP client not initialized")
    return _http

def safe_slug(s: str, max_len: int = 60) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if s else f"untitled_{uuid.uuid4().hex[:6]}"

async def wav_to_mp3(wav_path: str, mp3_path: str) -> None:
    try:
        clip = AudioFileClip(wav_path)
        clip.write_audiofile(mp3_path, codec="libmp3lame")
        clip.close()
    except Exception as e:
        log.exception("WAV→MP3 conversion failed")
        raise HTTPException(500, f"WAV→MP3 conversion failed: {e}")

# ----------------------------
# Models
# ----------------------------
class MetadataResponse(BaseModel):
    title: str
    tags: List[str]
    description: str

# ----------------------------
# Health
# ----------------------------
@app.get("/")
def root():
    return {"message": "BeatBank Final API is running 🚀", "replicate_model": REPLICATE_MODEL}

# ----------------------------
# Upload
# ----------------------------
@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    slug = safe_slug(file.filename.rsplit(".", 1)[0])
    ext = file.filename.rsplit(".", 1)[-1].lower()
    out_path = os.path.join(AUD_DIR, f"{slug}.{ext}")
    async with aiofiles.open(out_path, "wb") as f:
        await f.write(await file.read())
    return {"status": "success", "audio_path": out_path}

# ----------------------------
# Metadata (OpenAI)
# ----------------------------
@app.post("/api/metadata", response_model=MetadataResponse)
async def generate_metadata(prompt: str = Form(...)):
    system_prompt = (
        "You are a creative music branding assistant. "
        "Given a beat description, output compact JSON with keys: "
        "title (2–5 words), tags (3–6 items), description (1 concise line). "
        "Respond with JSON only."
    )
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.9,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content
        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "title": (raw or "Untitled Beat")[:40],
                "tags": ["beat", "ai", "music"],
                "description": (raw or "AI beat")[:160],
            }
        # Best-effort DB insert
        try:
            supabase.table("beats").insert({
                "file_name": None, "title": data["title"], "tags": data["tags"],
                "description": data["description"], "image_path": None
            }).execute()
        except Exception as e:
            log.warning("Supabase insert (metadata) warning: %s", e)
        return MetadataResponse(**data)
    except Exception as e:
        log.exception("Metadata generation failed")
        raise HTTPException(500, f"Metadata error: {e}")

# ----------------------------
# Image (OpenAI)
# ----------------------------
@app.post("/api/image")
async def generate_image(
    title: str = Form(...),
    tags: str = Form(""),
    description: str = Form("")
):
    prompt = (
        f"Album cover for a beat titled '{title}'. {description} "
        f"Vibes: {tags}. Square, clean, high-contrast, modern."
    )
    try:
        img = openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        b64 = img.data[0].b64_json
        data = base64.b64decode(b64)
        slug = safe_slug(title)
        path = os.path.join(IMG_DIR, f"{slug}.png")
        with open(path, "wb") as f:
            f.write(data)
        # Optional DB update
        try:
            supabase.table("beats").update({"image_path": path}) \
                .order("created_at", desc=True).limit(1).execute()
        except Exception as e:
            log.warning("Supabase update (image) warning: %s", e)
        return {"status": "success", "image_path": path, "prompt_used": prompt}
    except Exception as e:
        log.exception("Image generation failed")
        raise HTTPException(500, f"Image error: {e}")

# ----------------------------
# Music — Providers
# ----------------------------
def _ensure_replicate_ready():
    if not REPLICATE_API_TOKEN:
        raise HTTPException(500, "Missing REPLICATE_API_TOKEN in .env")
    if not _REPLICATE_AVAILABLE:
        raise HTTPException(
            500,
            "Replicate SDK not installed. Install with:\n"
            "  pip install replicate\n"
        )
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

async def _generate_elevenlabs_music(prompt: str, duration_seconds: int, slug: str) -> str:
    """
    ElevenLabs (via Replicate SDK)
    - output_format = mp3
    - force_instrumental = True
    - music_length_ms = duration_seconds * 1000 (clamped 1..300s)
    """
    _ensure_replicate_ready()

    dur = max(1, min(int(duration_seconds), 300))  # clamp 1..300s
    music_length_ms = dur * 1000

    model_ref = REPLICATE_MODEL if not REPLICATE_MODEL_VERSION else f"{REPLICATE_MODEL}:{REPLICATE_MODEL_VERSION}"

    log.info("[Replicate SDK] Running %s (duration=%ss, instrumental=True, format=mp3)", model_ref, dur)

    # Run model
    try:
        output = replicate.run(
            model_ref,
            input={
                "prompt": prompt,
                "output_format": "mp3_high_quality",
                "music_length_ms": music_length_ms,
                "force_instrumental": True
            }
        )
    except Exception as e:
        log.exception("Replicate SDK run failed")
        raise HTTPException(502, f"Replicate SDK error: {e}")

    # Replicate SDK returns a FileOutput-like object for file outputs
    try:
        # Prefer high-level helpers
        if isinstance(output, str):
            url = output
        elif isinstance(output, list) and output and isinstance(output[0], str):
            url = output[0]
        elif hasattr(output, "url"):
    # handle object-based outputs
            url = output.url() if callable(output.url) else output.url
        else:
            url = None

        if not url or not str(url).startswith("http"):
            raise HTTPException(502, f"ElevenLabs output missing valid URL: {repr(url)}")

        # Download to disk using SDK read() if available, else HTTP
        mp3_path = os.path.join(AUD_DIR, f"{slug}.mp3")
        if hasattr(output, "read"):
            with open(mp3_path, "wb") as f:
                f.write(output.read())
            return mp3_path

        # Fallback to HTTP download
        client = ensure_http()
        r = await client.get(url)
        r.raise_for_status()
        with open(mp3_path, "wb") as f:
            f.write(r.content)
        return mp3_path

    except HTTPException:
        raise
    except Exception as e:
        log.exception("Failed to process ElevenLabs file output")
        raise HTTPException(500, f"Failed to process ElevenLabs output: {e}")

# ----------------------------
# /api/music
# ----------------------------
@app.post("/api/music")
async def generate_music(
    prompt: str = Form(...),
    duration: int = Form(30),
    provider: Literal["auto", "replicate", "local"] = Form("auto"),
    output_format: Literal["mp3", "wav", "both"] = Form("mp3"),
    title_hint: Optional[str] = Form(None)
):
    slug = safe_slug(title_hint or prompt)
    target = provider if provider != "auto" else ("replicate" if REPLICATE_API_TOKEN else "local")

    paths: List[str] = []

    if target == "replicate":
        # Use ElevenLabs via Replicate SDK
        p = await _generate_elevenlabs_music(prompt, duration, slug)
        paths.append(p)
    elif target == "local":
        raise HTTPException(400, "Local MusicGen is disabled for now. Use provider=replicate (ElevenLabs).")
    else:
        raise HTTPException(400, "Unsupported provider")

    # 'both' not applicable since provider returns mp3 directly; we could add conversion if needed
    if output_format == "both":
        log.info("[Music] 'both' requested, but ElevenLabs already returns mp3; add WAV conversion if needed.")

    # DB insert
    try:
        supabase.table("beats").insert({
            "file_name": (paths or [None])[-1],
            "title": (title_hint or prompt)[:50],
            "tags": ["ai", target, "beat"],
            "description": f"Generated via {target} (ElevenLabs): {prompt}",
            "image_path": None
        }).execute()
    except Exception as e:
        log.warning("Supabase insert (music) warning: %s", e)

    return {"status": "success", "provider": target, "audio_paths": paths, "duration": duration}

# ----------------------------
# Visualizer
# ----------------------------
@app.post("/api/video")
async def generate_visualizer(
    title: str = Form(...),
    image_path: str = Form(...),
    audio_path: str = Form(...),
    duration: int = Form(10)
):
    slug = safe_slug(title)
    out_path = os.path.join(VID_DIR, f"{slug}.mp4")
    try:
        image = ImageClip(image_path, duration=duration)
        audio = AudioFileClip(audio_path).subclip(0, duration)
        video = image.set_audio(audio).fadein(0.5).fadeout(0.5)
        try:
            video = video.fx(vfx.zoom_in, 1.03)
        except Exception:
            pass
        video.write_videofile(out_path, fps=30, codec="libx264", audio_codec="aac")
        return {"status": "success", "title": title, "video_path": out_path}
    except Exception as e:
        log.exception("Visualizer failed")
        raise HTTPException(500, f"Visualizer error: {e}")

# ----------------------------
# Auto chain
# ----------------------------
@app.post("/api/auto")
async def auto_chain(
    prompt: str = Form(...),
    do_metadata: bool = Form(True),
    do_image: bool = Form(True),
    do_music: bool = Form(True),
    do_visualizer: bool = Form(True),
    do_ai_video: bool = Form(False),
    ai_video_provider: Literal["runway"] = Form("runway"),
    audio_path: Optional[str] = Form(None),
    image_path: Optional[str] = Form(None),
    duration: int = Form(30),
    audio_format: Literal["mp3", "wav", "both"] = Form("mp3"),
    provider: Literal["auto", "replicate", "local"] = Form("auto")
):
    result = {
        "prompt": prompt,
        "metadata": None,
        "image_path": image_path,
        "audio_paths": [audio_path] if audio_path else None,
        "video_path": None
    }

    if do_metadata:
        meta = await generate_metadata(prompt)
        result["metadata"] = meta.model_dump()
        title = result["metadata"]["title"]
        tags_str = ", ".join(result["metadata"]["tags"])
        desc = result["metadata"]["description"]
    else:
        title = safe_slug(prompt)
        tags_str, desc = "", ""

    if do_image and not image_path:
        img_json = await generate_image(title=title, tags=tags_str, description=desc)
        result["image_path"] = img_json["image_path"]

    if do_music and not audio_path:
        mus_json = await generate_music(
            prompt=prompt, duration=duration, provider=provider,
            output_format=audio_format, title_hint=title
        )
        result["audio_paths"] = mus_json["audio_paths"]

    if do_visualizer and result.get("image_path") and result.get("audio_paths"):
        main_audio = result["audio_paths"][-1]
        viz = await generate_visualizer(title=title, image_path=result["image_path"],
                                        audio_path=main_audio, duration=duration)
        result["video_path"] = viz["video_path"]

    # Best-effort DB insert
    try:
        supabase.table("beats").insert({
            "file_name": (result.get("audio_paths") or [None])[-1],
            "title": title[:50],
            "tags": result["metadata"]["tags"] if result["metadata"] else ["ai", "beat"],
            "description": desc or f"Auto-generated: {prompt}",
            "image_path": result.get("image_path")
        }).execute()
    except Exception as e:
        log.info("(non-fatal) Supabase final insert skipped/failed: %s", e)

    return {"status": "success", **result}
