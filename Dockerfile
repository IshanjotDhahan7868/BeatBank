# --- Backend container for BeatBank ---
FROM python:3.11-slim

# System packages MoviePy/librosa need
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg libsndfile1  && rm -rf /var/lib/apt/lists/*

# App workspace
WORKDIR /app

# Install deps first (best layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip  && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Ensure StaticFiles mount won't crash if folder missing
RUN mkdir -p /app/artifacts

# Start FastAPI on Railway-assigned port
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port $PORT"] 
