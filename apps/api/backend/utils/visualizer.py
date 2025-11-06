# backend/utils/visualizer.py

import os
import numpy as np
import librosa
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    VideoClip,
    CompositeVideoClip,
)
from moviepy.video.fx.all import colorx, fadein, fadeout

import random


class VisualizerEngine:

    def __init__(
        self,
        image_path: str,
        audio_path: str,
        duration: int,
        effects: dict,
        fps: int = 30,
    ):
        self.image_path = image_path
        self.audio_path = audio_path
        self.duration = duration
        self.effects = effects
        self.fps = fps

        # Load audio data
        self.y, self.sr = librosa.load(audio_path, sr=None)
        self.duration_audio = librosa.get_duration(y=self.y, sr=self.sr)

        # Precompute audio-reactive features
        self.onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr)
        self.rms = librosa.feature.rms(y=self.y)[0]
        self.spectrogram = np.abs(librosa.stft(self.y, n_fft=1024))

    # ------------------------------------------
    # UTILS: Audio-reactive helpers
    # ------------------------------------------
    def get_rms_at_time(self, t):
        idx = int((t / self.duration_audio) * len(self.rms))
        idx = np.clip(idx, 0, len(self.rms) - 1)
        return float(self.rms[idx])

    def get_spectrum_at_time(self, t):
        frame = int((t / self.duration_audio) * self.spectrogram.shape[1])
        frame = np.clip(frame, 0, self.spectrogram.shape[1] - 1)
        return self.spectrogram[:, frame]

    # ------------------------------------------
    # EFFECT: Pulse (RMS-based)
    # ------------------------------------------
    def effect_pulse(self, frame, t):
        rms = self.get_rms_at_time(t)
        strength = 1 + (rms * 2.5)
        return frame.resize(strength)

    # ------------------------------------------
    # EFFECT: Zoom Motion
    # ------------------------------------------
    def effect_zoom(self, frame, t):
        zoom = 1.02 + 0.005 * np.sin(t * 0.7)
        return frame.resize(zoom)

    # ------------------------------------------
    # EFFECT: VHS / Glitch
    # ------------------------------------------
    def effect_vhs(self, frame, t):
        shift = int(5 * np.sin(t * 25))
        return frame.crop(x1=shift, y1=0)

    # ------------------------------------------
    # EFFECT: Waveform Bars
    # ------------------------------------------
    def effect_waveform(self, t, w, h):
        spectrum = self.get_spectrum_at_time(t)
        bars = 100
        band = np.linspace(0, len(spectrum), bars).astype(int)
        values = spectrum[band] / np.max(spectrum[band] + 1e-6)

        overlay = np.zeros((h, w, 3), dtype=np.uint8)

        bar_width = w // bars

        for i, v in enumerate(values):
            height = int(v * h * 0.4)
            x1 = i * bar_width
            x2 = x1 + bar_width - 1
            y1 = h - height
            y2 = h
            overlay[y1:y2, x1:x2] = (0, 255, 200)

        return overlay

    # ------------------------------------------
    # RENDER
    # ------------------------------------------
    def build(self, output_path):

        bg = ImageClip(self.image_path).resize((1280, 720))

        def make_frame(t):
            frame = bg.get_frame(t)

            # Convert frame to MoviePy style
            frame_clip = ImageClip(frame)

            # Pulse
            if self.effects.get("pulse"):
                frame_clip = self.effect_pulse(frame_clip, t)

            # Zoom
            if self.effects.get("zoom"):
                frame_clip = self.effect_zoom(frame_clip, t)

            # VHS
            if self.effects.get("vhs"):
                frame_clip = self.effect_vhs(frame_clip, t)

            # Convert back to np array
            frame = frame_clip.get_frame(t)

            # Waveform
            if self.effects.get("waveform"):
                h, w, _ = frame.shape
                overlay = self.effect_waveform(t, w, h)
                frame = (0.7 * frame + 0.3 * overlay).astype(np.uint8)

            return frame

        # Create video
        video = VideoClip(make_frame, duration=self.duration)
        audio = AudioFileClip(self.audio_path)

        final = video.set_audio(audio)
        final.write_videofile(output_path, fps=self.fps, codec="libx264", audio_codec="aac")

        return output_path
