# backend/main.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import base64
from typing import Optional, Literal, List

import aiofiles
import httpx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from moviepy.editor import ImageClip, AudioFileClip, vfx
from openai import OpenAI


from utils.logging import setup_logger
from providers.video_runway import create_ai_video_with_audio
from utils.storage import safe_slug, IMG_DIR, VID_DIR, AUD_DIR, ensure_dirs
from utils.dsp import analyze_audio

from config import (
    OPENAI_API_KEY,
    SUPABASE_URL,
    SUPABASE_KEY,
    FRONTEND_URL,
)

from providers.music_replicate import generate_elevenlabs_music
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"


# Init
log = setup_logger()
ensure_dirs()

openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="BeatBank API", version="2025.11.06")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_http: Optional[httpx.AsyncClient] = None

# Mount artifacts folder for public serving
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)  # <-- add this line
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")


@app.on_event("startup")
async def _startup():
    global _http
    _http = httpx.AsyncClient(timeout=600)
    log.info("BeatBank API online")


@app.on_event("shutdown")
async def _shutdown():
    global _http
    if _http:
        await _http.aclose()
        log.info("HTTP client closed")


def http_client() -> httpx.AsyncClient:
    if not _http:
        raise RuntimeError("HTTP client not initialized")
    return _http


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
    return {"message": "BeatBank API is running 🚀"}


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
# Metadata
# ----------------------------
@app.post("/api/metadata", response_model=MetadataResponse)
async def generate_metadata(prompt: str = Form(...)):
    system_prompt = (
        "You are a creative music branding assistant. "
        "Given a beat description, output compact JSON with keys: "
        "title, tags, description. Respond with JSON only."
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
        except:
            data = {
                "title": (raw or "Untitled")[:40],
                "tags": ["ai", "beat"],
                "description": (raw or "")[:160],
            }

        # store minimal data
        try:
            supabase.table("beats").insert({
                "file_name": None,
                "title": data["title"],
                "tags": data["tags"],
                "description": data["description"],
                "image_path": None,
            }).execute()
        except Exception as e:
            log.warning(f"Supabase insert warning: {e}")

        return data

    except Exception as e:
        log.exception("Metadata failed")
        raise HTTPException(500, f"Metadata error: {e}")


# ----------------------------
# Image Generation
# ----------------------------
@app.post("/api/image")
async def generate_image(
    title: str = Form(...),
    tags: str = Form(""),
    description: str = Form(""),
):
    prompt = (
        f"Album cover for a beat titled '{title}'. {description} "
        f"Vibes: {tags}. Square, high-contrast, modern."
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

        return {"status": "success", "image_path": path}

    except Exception as e:
        log.exception("Image failed")
        raise HTTPException(500, f"Image error: {e}")


# ----------------------------
# Music Generation (Replicate)
# ----------------------------
@app.post("/api/music")
async def generate_music(
    prompt: str = Form(...),
    duration: int = Form(30),
    provider: Literal["auto", "replicate", "local"] = Form("auto"),
    output_format: Literal["mp3", "wav", "both"] = Form("mp3"),
    title_hint: Optional[str] = Form(None),
):
    slug = safe_slug(title_hint or prompt)

    if provider not in ("auto", "replicate"):
        raise HTTPException(400, "Only replicate provider supported.")

    mp3_path = await generate_elevenlabs_music(
        prompt=prompt,
        duration_seconds=duration,
        slug=slug,
        client=http_client(),
    )

    return {"status": "success", "audio_paths": [mp3_path]}


# ----------------------------
# Visualizer (NEW)
# ----------------------------
@app.post("/api/video")
async def generate_visualizer(
    title: str = Form(...),
    image_path: str = Form(...),
    audio_path: str = Form(...),
    duration: int = Form(10),

    # NEW visualizer toggles
    waveform: bool = Form(False),
    spectrum: bool = Form(False),
    pulse: bool = Form(False),
    zoom: bool = Form(False),
    vhs: bool = Form(False),
):
    from utils.visualizer import VisualizerEngine  # import new engine

    slug = safe_slug(title)
    out_path = os.path.join(VID_DIR, f"{slug}.mp4")

    try:
        engine = VisualizerEngine(
            image_path=image_path,
            audio_path=audio_path,
            duration=duration,
            effects={
                "waveform": waveform,
                "spectrum": spectrum,
                "pulse": pulse,
                "zoom": zoom,
                "vhs": vhs,
            },
        )

        engine.build(out_path)
        return {"status": "success", "video_path": out_path}

    except Exception as e:
        log.exception("Visualizer failed")
        raise HTTPException(500, f"Visualizer error: {e}")


# ----------------------------
# AI Video (Runway)
# ----------------------------
@app.post("/api/ai_video")
async def ai_video_endpoint(
    prompt: str = Form(...),
    duration: int = Form(6),                  # keep short for speed/cost
    audio_path: Optional[str] = Form(None),   # optional overlay
    title_hint: Optional[str] = Form(None),
):
    try:
        res = await create_ai_video_with_audio(
            prompt=prompt,
            duration=duration,
            audio_path=audio_path,
            title_hint=title_hint or prompt,
            client=http_client(),
        )
        return {"status": "success", **res}
    except Exception as e:
        raise HTTPException(500, f"AI video error: {e}")
    

# ----------------------------
# DETAIL
# ----------------------------
@app.get("/api/detail/{beat_id}")
async def get_detail(beat_id: int):
    try:
        res = supabase.table("beats").select("*").eq("id", beat_id).single().execute()
        if not res.data:
            raise HTTPException(404, "Beat not found")

        # Normalize JSON strings (common in your table)
        row = res.data
        title = row.get("title")
        tags = row.get("tags")
        description = row.get("description")

        # Try parsing JSON if stored as a string
        if isinstance(title, str) and title.strip().startswith("{"):
            try:
                parsed = json.loads(title)
                title = parsed.get("title", title)
                tags = parsed.get("tags", tags)
                description = parsed.get("description", description)
            except:
                pass

        return {
            "status": "success",
            "data": {
                "id": row.get("id"),
                "title": title,
                "tags": tags,
                "description": description,
                "image_path": row.get("image_path"),
                "video_path": row.get("video_path"),
                "ai_video_path": row.get("ai_video_path"),
                "file_name": row.get("file_name"),
                "created_at": row.get("created_at"),
            }
        }

    except Exception as e:
        log.exception("Detail fetch failed")
        raise HTTPException(500, f"Detail fetch error: {e}")



# ----------------------------
# HISTORY (fixed)
# ----------------------------
@app.get("/api/history")
async def get_history():
    try:
        res = supabase.table("beats").select("*").order("id", desc=True).execute()
        rows = res.data or []

        cleaned = []
        for r in rows:
            # Handle cases where title or tags are stored as JSON text
            title = r.get("title")
            tags = r.get("tags")
            desc = r.get("description")

            # try parsing JSON if stored as string
            if isinstance(title, str) and title.strip().startswith("{"):
                try:
                    parsed = json.loads(title)
                    title = parsed.get("title", title)
                    tags = parsed.get("tags", tags)
                    desc = parsed.get("description", desc)
                except Exception:
                    pass

            cleaned.append({
                "id": r.get("id"),
                "title": title or "Untitled",
                "tags": tags or [],
                "description": desc or "",
                "image_path": r.get("image_path"),
                "video_path": r.get("video_path"),
                "ai_video_path": r.get("ai_video_path"),
                "file_name": r.get("file_name"),
                "created_at": r.get("created_at"),
            })

        return {"status": "success", "data": cleaned}

    except Exception as e:
        log.exception("History fetch failed")
        raise HTTPException(500, f"History fetch error: {e}")




# ----------------------------
# AUTO PIPELINE
# ----------------------------
@app.post("/api/auto")
async def auto_chain(
    request: Request,
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
    provider: Literal["auto", "replicate", "local"] = Form("auto"),
):

    result = {
        "prompt": prompt,
        "metadata": None,
        "image_path": image_path,
        "audio_paths": [audio_path] if audio_path else None,
        "video_path": None,
        "ai_video_path": None,
        "dsp": None,
    }

    # ----------------------------
    # 1) METADATA
    # ----------------------------
    if do_metadata:
        meta = await generate_metadata(prompt)
        result["metadata"] = meta
        title = meta["title"]
        tags_str = ", ".join(meta["tags"])
        desc = meta["description"]
    else:
        title = safe_slug(prompt)
        tags_str = ""
        desc = ""

    # ----------------------------
    # 2) IMAGE GENERATION
    # ----------------------------
    if do_image and not image_path:
        img_json = await generate_image(
            title=title,
            tags=tags_str,
            description=desc
        )
        result["image_path"] = img_json["image_path"]

    # ----------------------------
    # 3) MUSIC GENERATION
    # ----------------------------
    if do_music and not audio_path:
        mus_json = await generate_music(
            prompt=prompt,
            duration=duration,
            provider=provider,
            output_format=audio_format,
            title_hint=title,
        )
        result["audio_paths"] = mus_json["audio_paths"]

    # ----------------------------
    # 4) DSP ANALYSIS
    # ----------------------------
    if result["audio_paths"]:
        try:
            dsp_data = analyze_audio(result["audio_paths"][-1])
            result["dsp"] = dsp_data
        except Exception as e:
            log.warning(f"DSP analysis failed: {e}")
            result["dsp"] = None

    # ----------------------------
    # 5) OPTIONAL: AI VIDEO GENERATION (Runway)
    # ----------------------------
    if do_ai_video:
        try:
            from providers.video_runway import create_ai_video_with_audio

            main_audio = (result["audio_paths"] or [None])[-1]

            ai_res = await create_ai_video_with_audio(
                prompt=prompt,
                duration=min(duration, 10),   # avoid expensive long videos
                audio_path=main_audio,
                title_hint=title,
                client=http_client(),
            )

            result["ai_video_path"] = ai_res.get("ai_video_final_path")

        except Exception as e:
            log.warning(f"AI Video generation failed: {e}")
            result["ai_video_path"] = None

    # ----------------------------
    # 6) VISUALIZER (only if NOT using AI video)
    # ----------------------------
    if do_visualizer and result["image_path"] and result["audio_paths"]:
        try:
            main_audio = result["audio_paths"][-1]

            viz = await generate_visualizer(
                title=title,
                image_path=result["image_path"],
                audio_path=main_audio,
                duration=duration,
                waveform=True,
                spectrum=False,
                pulse=True,
                zoom=True,
                vhs=False,
            )

            result["video_path"] = viz["video_path"]
        except Exception as e:
            log.warning(f"Visualizer failed: {e}")

# ----------------------------
# 7) SAVE TO SUPABASE
# ----------------------------
try:
    user_id = request.headers.get("x-user-id")  # 🔥 ADDED

    dsp = result["dsp"] or {}

    supabase.table("beats").insert({
        "user_id": user_id,                                  # 🔥 ADDED
        "file_name": (result["audio_paths"] or [None])[-1],
        "title": title[:50],
        "tags": result["metadata"]["tags"] if result["metadata"] else ["ai"],
        "description": desc,
        "image_path": result["image_path"],
        "video_path": result.get("video_path"),
        "ai_video_path": result.get("ai_video_path"),

        # DSP
        "bpm": dsp.get("bpm"),
        "key": dsp.get("key"),
        "energy": dsp.get("energy_rms"),
        "brightness": dsp.get("brightness"),
        "dynamic_range": dsp.get("dynamic_range"),
        "tempo_stability": dsp.get("tempo_stability"),
        "duration_sec": dsp.get("duration_sec"),
    }).execute()

except Exception as e:
    log.info(f"Supabase insert (non-fatal): {e}")


