FROM python:3.11-slim

# System deps for moviepy, librosa, etc  
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy REAL backend requirements
COPY backend/requirements.txt ./requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Prevent StaticFiles errors
RUN mkdir -p /app/artifacts

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
