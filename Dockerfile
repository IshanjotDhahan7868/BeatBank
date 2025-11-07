FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first
COPY backend/requirements.txt ./requirements.txt

# FIX: Install moviepy + imageio + imageio-ffmpeg manually
RUN pip install --upgrade pip
RUN pip install moviepy imageio imageio-ffmpeg

# Install your other deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ /app/

# Ensure folder exists
RUN mkdir -p /app/artifacts

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
