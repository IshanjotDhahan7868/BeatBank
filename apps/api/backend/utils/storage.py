# backend/utils/storage.py
import os
import re
import uuid

# Base artifacts dir colocated with backend
ART_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
IMG_DIR = os.path.join(ART_DIR, "images")
VID_DIR = os.path.join(ART_DIR, "videos")
AUD_DIR = os.path.join(ART_DIR, "audio")

def ensure_dirs():
    for d in (ART_DIR, IMG_DIR, VID_DIR, AUD_DIR):
        os.makedirs(d, exist_ok=True)

def safe_slug(s: str, max_len: int = 60) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] if s else f"untitled_{uuid.uuid4().hex[:6]}"
