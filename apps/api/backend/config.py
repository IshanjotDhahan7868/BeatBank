# backend/config.py

import os
from dotenv import load_dotenv

# --- Load .env from parent directory ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

# --- Environment Variables ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = os.getenv("REPLICATE_MODEL", "elevenlabs/music")
REPLICATE_MODEL_VERSION = os.getenv("REPLICATE_MODEL_VERSION", "")

RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
SUNO_BASE = os.getenv("SUNO_BASE", "")
HF_API_KEY = os.getenv("HF_API_KEY", "")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# --- Validate Core Env ---
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")

# --- Storage Directories ---
ART_DIR = "artifacts"
IMG_DIR = os.path.join(ART_DIR, "images")
VID_DIR = os.path.join(ART_DIR, "videos")
AUD_DIR = os.path.join(ART_DIR, "audio")

# Create directories if missing
for d in (ART_DIR, IMG_DIR, VID_DIR, AUD_DIR):
    os.makedirs(d, exist_ok=True)
