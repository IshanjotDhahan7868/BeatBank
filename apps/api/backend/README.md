# 🎧 BeatBank API — MVP (v0.1)
An AI-powered automated beat generator pipeline built with FastAPI.  
Generates **metadata → cover art → music → visualizer → AI video (coming soon)**, and stores results in Supabase.

This MVP is structured, modular, and production-ready for deployment or review by senior developers.

---

## ✅ Features

### ✅ AI Metadata Generation (OpenAI)
- Title, tags, and description based on a text prompt
- Stored automatically in Supabase

### ✅ AI Cover Art (OpenAI Image Models)
- High resolution 1024x1024 album-style artwork
- Saved to `artifacts/images/`

### ✅ AI Music Generation (Replicate – ElevenLabs Music)
- 30–300 second instrumental beats
- MP3 downloaded directly from Replicate CDN
- Saved to `artifacts/audio/`

### ✅ Video Visualizer
- Zoom-in cinematic loop with audio overlay
- Saved to `artifacts/videos/`

### ✅ Auto Mode (`/api/auto`)
One request generates everything:
metadata → artwork → music → visualizer

### ✅ Modular Backend Architecture
- `providers/` for external AI services  
- `utils/` for storage, DSP, logging  
- `config.py` for environment and directory management  
- `main.py` stays clean and readable  

---

## ✅ Project Structure

apps/api/
│
└── backend/
├── main.py # FastAPI app / endpoints
├── config.py # env loader + directory config
│
├── providers/
│ ├── music_replicate.py # ElevenLabs/Replicate music API
│ └── video_runway.py # (Nov 7) Runway/Pika integration
│
├── utils/
│ ├── logging.py # unified logging system
│ ├── storage.py # slugify + artifacts folder mgmt
│ └── dsp.py # (Nov 6) BPM/Key analysis
│
├── artifacts/
│ ├── images/
│ ├── videos/
│ └── audio/
│
└── requirements.txt

---

## ✅ Setup

### 1. Clone repo
git clone <https://github.com/IshanjotDhahan7868/BeatBank.git>
cd apps/api/backend

shell
Copy code

### 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

shell
Copy code

### 3. Install dependencies
pip install -r requirements.txt

shell
Copy code

### 4. Create `.env` file
OPENAI_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

REPLICATE_API_TOKEN=your_token
REPLICATE_MODEL=elevenlabs/music
REPLICATE_MODEL_VERSION=

RUNWAY_API_KEY=your_key
SUNO_BASE=https://api.sunoapi.org
HF_API_KEY=your_hf_token

FRONTEND_URL=http://localhost:5173

markdown
Copy code

### 5. Run server
From inside the **backend** folder:

uvicorn main:app --reload

arduino
Copy code

Server runs at:
http://127.0.0.1:8000

yaml
Copy code

Swagger UI:
http://127.0.0.1:8000/docs

yaml
Copy code

---

## ✅ Endpoints

### **GET /**  
Health check.

### **POST /api/metadata**
Generate title, description, tags.

### **POST /api/image**
Generate album artwork based on metadata.

### **POST /api/music**
Generate instrumental MP3 using ElevenLabs (Replicate).

### **POST /api/video**
Build a simple video visualizer.

### **POST /api/auto**
Run the whole chain:
prompt → metadata → image → music → visualizer

yaml
Copy code

---

## ✅ Environment Variables

All env variables are loaded from `.env` via `config.py`:

| Variable | Description |
|---------|-------------|
| OPENAI_API_KEY | OpenAI models |
| SUPABASE_URL | Supabase project |
| SUPABASE_KEY | Supabase anon key |
| REPLICATE_API_TOKEN | Replicate access |
| RUNWAY_API_KEY | Runway Gen-2/3 (Nov 7) |
| HF_API_KEY | HuggingFace backup (optional) |
| FRONTEND_URL | Vite/React frontend domain |

---

## ✅ Artifacts

Generated files land in:

backend/artifacts/
images/
videos/
audio/

yaml
Copy code

These paths are managed by `utils/storage.py`.

---

## ✅ Roadmap (Week-1 MVP)

### ✅ Nov 5 — Backend cleanup (done)
- Folder structure
- Config separation
- Logging system
- Providers modularized
- Artifacts clean

### ✅ Nov 6 — DSP Audio Analysis
- BPM
- Key
- Energy
- Brightness
- Tempo stability
- Combine with GPT metadata

### ✅ Nov 7 — AI Video Provider
- Runway Gen-3 / Pika integration
- Async polling
- Audio overlay
- Store ai_video_path

### ✅ Nov 8 — Frontend (React + Tailwind)
- Generate page
- History page
- Detail view

### ✅ Nov 9 — Deployment
- Railway backend
- Vercel frontend

### ✅ Nov 10–11 — Polish + Handoff
- Improved error handling
- Screenshots
- Documentation
- Demo video

---

## ✅ License
MIT

---

## ✅ Author
**Ishanjot (ProdByShan)**  
AI-powered beat automation & software developer.

