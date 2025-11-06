# backend/utils/dsp.py

import librosa
import numpy as np

def analyze_audio(audio_path: str) -> dict:
    """
    Analyze an audio file and extract musical features:
    - BPM (tempo)
    - Key + confidence
    - Energy (RMS)
    - Brightness (spectral centroid)
    - Dynamic range
    - Tempo stability
    - Duration
    """

    try:
        # Load audio (mono)
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        # Duration
        duration_sec = librosa.get_duration(y=y, sr=sr)

        # BPM
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo)

        # Tempo stability (are beats evenly spaced?)
        if len(beat_frames) > 1:
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            diffs = np.diff(beat_times)
            tempo_stability = float(1.0 - np.std(diffs))  # closer to 1 = stable
        else:
            tempo_stability = 0.0

        # Energy (RMS)
        rms = librosa.feature.rms(y=y)
        energy_rms = float(np.mean(rms))

        # Brightness (Spectral Centroid)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        brightness = float(np.mean(centroid))

        # Dynamic range (max - min energy)
        dynamic_range = float(np.max(rms) - np.min(rms))

        # ---- KEY DETECTION ----
        # Compute chroma (12-bin pitch class feature)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)

        key_index = int(np.argmax(chroma_mean))
        key_confidence = float(np.max(chroma_mean))

        # Map to musical keys
        KEY_MAP = [
            "C", "C#", "D", "D#", "E", "F",
            "F#", "G", "G#", "A", "A#", "B"
        ]
        detected_key = KEY_MAP[key_index]

        return {
            "bpm": bpm,
            "key": detected_key,
            "key_confidence": key_confidence,
            "energy_rms": energy_rms,
            "brightness": brightness,
            "dynamic_range": dynamic_range,
            "tempo_stability": tempo_stability,
            "duration_sec": duration_sec
        }

    except Exception as e:
        return {"error": str(e)}
