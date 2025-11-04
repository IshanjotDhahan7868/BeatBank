import aiofiles
import os
import base64
import json
import httpx
import asyncio
import uuid
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import create_client, Client
from fastapi import FastAPI, UploadFile, Form
from moviepy.editor import ImageClip, AudioFileClip, VideoFileClip, vfx

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize Suno Client
SUNO_API_KEY = os.getenv("SUNO_API_KEY")
SUNO_BASE = "https://api.sunoapi.org"

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize Runway Client
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
RUNWAY_BASE = "https://api.runwayml.com/v1"

# Create FastAPI app
app = FastAPI(title="BeatBank API")

# ----- Data Model -----

class MetadataResponse(BaseModel):
    title: str
    tags: list[str]
    description: str


# ----- ROUTE: Upload file -----
@app.post("/api/generate")
async def generate(file: UploadFile, prompt: str = Form(...)):
    os.makedirs("artifacts", exist_ok=True)
    save_path = f"artifacts/{file.filename}"

    async with aiofiles.open(save_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    return {
        "status": "success",
        "message": f"Received {file.filename} with prompt: {prompt}"
    }


# ----- ROUTE: Root -----
@app.get("/")
def root():
    return {"message": "BeatBank backend is running 🚀"}


# ----- ROUTE: Metadata -----
@app.post("/api/metadata", response_model=MetadataResponse)
async def generate_metadata(prompt: str = Form(...)):
    """Generate beat metadata from a user prompt."""

    system_prompt = """
    You are a creative music branding assistant.
    Given a short description of a beat, produce:
    1. A catchy title (2–4 words)
    2. 3–5 descriptive tags
    3. A short one-line description.
    Respond strictly as JSON with keys:
    title, tags, description.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
        max_tokens=150,
    )

    # Parse safely
    try:
        data = json.loads(response.choices[0].message.content)
    except Exception:
        text = response.choices[0].message.content
        data = {
            "title": text.splitlines()[0][:30],
            "tags": ["beat", "ai", "music"],
            "description": text[:100]
        }

    # Insert metadata into Supabase
    record = {
        "file_name": "unknown.mp3",  # Replace later when you add file upload
        "title": data["title"],
        "tags": data["tags"],
        "description": data["description"],
        "image_path": None
    }

    try:
        supabase.table("beats").insert(record).execute()
    except Exception as e:
        print("Supabase insert error:", e)

    return MetadataResponse(**data)


# ----- ROUTE: Image generation -----
@app.post("/api/image")
async def generate_image(
    title: str = Form(...),
    tags: str = Form(...),
    description: str = Form(...)
):
    """Generate album art image from metadata"""

    prompt = (
        f"Album cover art for a beat titled '{title}', {description}. "
        f"Include visual vibes of {tags}. Cinematic, detailed, artistic."
    )

    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        os.makedirs("artifacts/images", exist_ok=True)
        path = f"artifacts/images/{title.replace(' ', '_')}.png"

        with open(path, "wb") as f:
            f.write(image_bytes)

        # Update latest record with image path
        try:
            supabase.table("beats") \
                .update({"image_path": path}) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
        except Exception as e:
            print("Supabase update error:", e)

        return {
            "status": "success",
            "prompt_used": prompt,
            "image_path": path
        }

    except Exception as e:
        return {"error": str(e)}


# ----- ROUTE: List all beats -----
@app.get("/api/beats")
def list_beats():
    data = supabase.table("beats").select("*").order("created_at", desc=True).execute()
    return data.data



@app.post("/api/video")
async def generate_video(
    title: str = Form(...),
    image_path: str = Form(...),
    audio_path: str = Form(...),
    duration: int = Form(10)
):
    """Generate a short looping visualizer video from image + audio"""

    os.makedirs("artifacts/videos", exist_ok=True)
    output_path = f"artifacts/videos/{title.replace(' ', '_')}.mp4"

    try:
        # Load image and audio
        image = ImageClip(image_path, duration=duration)
        audio = AudioFileClip(audio_path).subclip(0, duration)
        video = image.set_audio(audio)

        # Subtle motion effects
        video = video.fx(vfx.zoom_in, 1.03).fadein(1).fadeout(1)

        # Export the video
        video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")

        # Update Supabase record
        try:
            supabase.table("beats") \
                .update({"video_path": output_path}) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
        except Exception as e:
            print("Supabase update error:", e)

        return {
            "status": "success",
            "title": title,
            "video_path": output_path
        }

    except Exception as e:
        return {"error": str(e)}

@app.post("/api/video/ai")
async def generate_ai_video(
    prompt: str = Form(...),
    image_path: str = Form(None),
    audio_path: str = Form(None),
    duration: int = Form(10)
):
    """
    Generate cinematic AI video using Runway's Gen-2 model.
    Optionally attach audio and apply minor post-processing.
    """

    if not RUNWAY_API_KEY:
        raise HTTPException(status_code=500, detail="Missing RUNWAY_API_KEY in .env")

    # 1️⃣ Create Runway job
    data = {"model": "gen2", "prompt": prompt, "duration": duration}
    files = None
    if image_path and os.path.exists(image_path):
        files = {"image": open(image_path, "rb")}
    headers = {"Authorization": f"Bearer {RUNWAY_API_KEY}"}

    async with httpx.AsyncClient(timeout=300) as client:
        res = await client.post(f"{RUNWAY_BASE}/generations", headers=headers, data=data, files=files)
        if res.status_code != 200:
            raise HTTPException(res.status_code, f"Runway API error: {res.text}")
        job = res.json()
        job_id = job.get("id")

        # 2️⃣ Poll for completion
        for _ in range(90):
            poll = await client.get(f"{RUNWAY_BASE}/generations/{job_id}", headers=headers)
            j = poll.json()
            if j.get("status") == "succeeded":
                video_url = j["output"][0]["url"]
                break
            elif j.get("status") == "failed":
                raise HTTPException(500, f"Runway generation failed: {j}")
            await asyncio.sleep(5)
        else:
            raise HTTPException(504, "Runway job timeout")

        # 3️⃣ Download video
        os.makedirs("artifacts/videos", exist_ok=True)
        ai_path = f"artifacts/videos/ai_{job_id}.mp4"
        v = await client.get(video_url)
        v.raise_for_status()
        with open(ai_path, "wb") as f:
            f.write(v.content)

    # 4️⃣ Optional: attach audio (if provided)
    final_path = ai_path
    if audio_path and os.path.exists(audio_path):
        try:
            video_clip = VideoFileClip(ai_path).subclip(0, duration)
            audio_clip = AudioFileClip(audio_path).subclip(0, duration)
            final_clip = video_clip.set_audio(audio_clip)
            final_path = f"artifacts/videos/final_{job_id}.mp4"
            final_clip.write_videofile(final_path, fps=30, codec="libx264", audio_codec="aac")
        except Exception as e:
            print("MoviePy post-processing error:", e)

    # 5️⃣ Save path to Supabase
    try:
        supabase.table("beats") \
            .update({"video_path": final_path}) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
    except Exception as e:
        print("Supabase update error:", e)

    return {
        "status": "success",
        "provider": "runway",
        "prompt": prompt,
        "video_url": video_url,
        "video_path": final_path
    }

@app.post("/api/music")
async def generate_music(
    prompt: str = Form(...),
    mode: str = Form("instrumental"),
    duration: int = Form(180)  # up to 3 min
):
    """
    Generate full-length instrumental music using Meta's MusicGen (via Hugging Face API).
    """
    HF_API_KEY = os.getenv("HF_API_KEY")
    if not HF_API_KEY:
        raise HTTPException(500, "Missing HF_API_KEY in .env")

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    data = {
        "inputs": prompt,
        "parameters": {"duration": duration},
    }

    async with httpx.AsyncClient(timeout=None) as client:
        res = await client.post(
            "https://router.huggingface.co/hf-inference/models/facebook/musicgen-medium" ,

            headers=headers,
            json=data
        )
        if res.status_code != 200:
            raise HTTPException(res.status_code, f"MusicGen error: {res.text}")

        audio_bytes = res.content
        os.makedirs("artifacts/audio", exist_ok=True)
        beat_id = str(uuid.uuid4())[:8]
        file_path = f"artifacts/audio/beat_{beat_id}.wav"
        with open(file_path, "wb") as f:
            f.write(audio_bytes)

    # Optional: push metadata to Supabase
    try:
        supabase.table("beats").insert({
            "file_name": file_path,
            "title": prompt[:50],
            "tags": [mode, "musicgen", "ai"],
            "description": f"AI-generated {mode} track: {prompt}"
        }).execute()
    except Exception as e:
        print("Supabase insert error:", e)

    return {
        "status": "success",
        "provider": "MusicGen",
        "prompt": prompt,
        "audio_path": file_path,
        "duration": duration
    }

# ----- ROUTE: Auto Generate (Full Chain) -----
@app.post("/api/auto_generate")
async def auto_generate(prompt: str = Form(...), duration: int = Form(30)):
    """
    Fully automate the BeatBank pipeline:
    1. Generate music (Suno)
    2. Generate metadata (GPT)
    3. Generate cover art (DALL·E)
    4. Generate visualizer (MoviePy)
    5. Save everything to Supabase
    """

    try:
        async with httpx.AsyncClient(timeout=1200) as client:
            # 1️⃣ Generate music
            music_res = await client.post(
                "http://127.0.0.1:8000/api/music",
                data={"prompt": prompt, "mode": "instrumental", "duration": duration}
            )
            music_json = music_res.json()
            audio_path = music_json.get("audio_path")

            if not audio_path:
                raise HTTPException(500, "Music generation failed.")

            # 2️⃣ Generate metadata
            meta_res = await client.post(
                "http://127.0.0.1:8000/api/metadata",
                data={"prompt": prompt}
            )
            meta_json = meta_res.json()
            title = meta_json.get("title")
            tags = ", ".join(meta_json.get("tags", []))
            description = meta_json.get("description")

            # 3️⃣ Generate image
            img_res = await client.post(
                "http://127.0.0.1:8000/api/image",
                data={
                    "title": title,
                    "tags": tags,
                    "description": description
                }
            )
            img_json = img_res.json()
            image_path = img_json.get("image_path")

            # 4️⃣ Generate video
            vid_res = await client.post(
                "http://127.0.0.1:8000/api/video",
                data={
                    "title": title,
                    "image_path": image_path,
                    "audio_path": audio_path,
                    "duration": duration
                }
            )
            vid_json = vid_res.json()
            video_path = vid_json.get("video_path")

        # 5️⃣ Save full package in Supabase
        try:
            supabase.table("beats").insert({
                "file_name": audio_path,
                "title": title,
                "tags": meta_json.get("tags"),
                "description": description,
                "image_path": image_path,
                "video_path": video_path
            }).execute()
        except Exception as e:
            print("Supabase insert error:", e)

        return {
            "status": "success",
            "prompt": prompt,
            "title": title,
            "audio_path": audio_path,
            "image_path": image_path,
            "video_path": video_path,
            "metadata": meta_json
        }

    except Exception as e:
        print("Auto generation error:", e)
        raise HTTPException(500, detail=f"Auto generation failed: {str(e)}")
