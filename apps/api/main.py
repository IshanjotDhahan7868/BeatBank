import aiofiles
import os
import base64
import json
import httpx
import asyncio
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import HTTPException
from supabase import create_client, Client
from fastapi import FastAPI, UploadFile, Form
from moviepy.editor import ImageClip, AudioFileClip, vfx

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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