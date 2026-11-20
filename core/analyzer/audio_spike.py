import os
import subprocess
import numpy as np
import wave
from typing import List, Dict

class AudioSpikeAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def extract_audio_wav(self, video_path: str, wav_path: str) -> str:
        """Extract audio stream to a mono WAV file for fast NumPy processing."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",
            "-ac", "1",
            "-ar", str(self.sample_rate),
            "-f", "wav",
            wav_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr.decode('utf-8', errors='ignore')}")
        return wav_path

    def analyze_highlights(
        self,
        video_path: str,
        clip_duration: int = 30,
        pre_roll: int = 8,
        top_k: int = 3,
        mode: str = "gaming"
    ) -> List[Dict]:
        """
        Analyze audio energy and find top highlight moments.
        Adapts weights and pre-roll based on mode (gaming, podcast, talking_head).
        Returns list of clips with start_time, end_time, spike_time, and intensity score.
        """
        temp_wav = os.path.splitext(video_path)[0] + "_temp_audio.wav"
        try:
            self.extract_audio_wav(video_path, temp_wav)
            with wave.open(temp_wav, "rb") as wf:
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                audio_bytes = wf.readframes(n_frames)

            # Convert to numpy float32 array
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            total_duration = len(audio_data) / framerate

            if total_duration < clip_duration:
                return [{
                    "start": 0,
                    "end": total_duration,
                    "spike_time": total_duration / 2,
                    "score": 1.0
                }]

            # Configure weights and parameters based on content mode
            if mode == "podcast":
                w_loudness = 0.70
                w_delta = 0.30
                pre_roll = max(pre_roll, 12)  # More context for dialog flow
                kernel_size = 30             # Longer baseline smoothing for conversations
            elif mode == "talking_head":
                w_loudness = 0.55
                w_delta = 0.45
                pre_roll = max(pre_roll, 6)
                kernel_size = 20
            else:  # gaming
                w_loudness = 0.35
                w_delta = 0.65               # High sensitivity to sudden screams, claps, explosions
                pre_roll = max(pre_roll, 8)
                kernel_size = 18

            # Calculate RMS energy per 0.5 second window
            hop_size = int(framerate * 0.5)
            n_windows = len(audio_data) // hop_size
            rms_values = []
            timestamps = []

            for i in range(n_windows):
                window = audio_data[i * hop_size : (i + 1) * hop_size]
                rms = np.sqrt(np.mean(window ** 2) + 1e-9)
                rms_values.append(rms)
                timestamps.append(i * 0.5)

            rms_values = np.array(rms_values)
            timestamps = np.array(timestamps)

            # Convert to dB relative to max
            max_rms = np.max(rms_values) if np.max(rms_values) > 0 else 1.0
            db_values = 20 * np.log10(rms_values / max_rms + 1e-9)

            # Rolling baseline
            kernel = np.ones(kernel_size) / kernel_size
            baseline = np.convolve(db_values, kernel, mode="same")

            # Spike delta = how much higher than surrounding context
            delta = db_values - baseline

            # Combined score
            norm_db = (db_values - np.min(db_values)) / (np.max(db_values) - np.min(db_values) + 1e-9)
            norm_delta = (delta - np.min(delta)) / (np.max(delta) - np.min(delta) + 1e-9)
            scores = (w_loudness * norm_db) + (w_delta * norm_delta)

            # Find peak candidates
            ranked_indices = np.argsort(scores)[::-1]

            highlights = []
            used_ranges = []

            for idx in ranked_indices:
                spike_sec = float(timestamps[idx])
                start_sec = max(0.0, spike_sec - pre_roll)
                end_sec = min(total_duration, start_sec + clip_duration)
                if end_sec - start_sec < clip_duration:
                    start_sec = max(0.0, end_sec - clip_duration)

                # Check overlap (at least 20s gap)
                overlap = False
                for u_start, u_end in used_ranges:
                    if not (end_sec <= u_start or start_sec >= u_end):
                        overlap = True
                        break

                if not overlap:
                    highlights.append({
                        "start": round(start_sec, 2),
                        "end": round(end_sec, 2),
                        "spike_time": round(spike_sec, 2),
                        "score": round(float(scores[idx]), 3)
                    })
                    used_ranges.append((start_sec, end_sec))

                if len(highlights) >= top_k:
                    break

            return highlights

        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
