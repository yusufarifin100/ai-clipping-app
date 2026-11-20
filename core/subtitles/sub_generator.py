import os
import subprocess
import re
from typing import Optional, Dict, List, Tuple

class SubtitleGenerator:
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            import whisper
            print(f"[SubtitleGenerator] Loading Whisper model: '{self.model_name}'...")
            self._model = whisper.load_model(self.model_name)
        return self._model

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds into ASS timestamp: H:MM:SS.cc"""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centi = int(round((seconds - int(seconds)) * 100))
        if centi >= 100:
            secs += 1
            centi = 0
        return f"{hrs}:{mins:02d}:{secs:02d}.{centi:02d}"

    def generate_subtitles(
        self,
        audio_or_video_path: str,
        output_ass_path: str,
        max_words_per_line: int = 5
    ) -> Tuple[str, str]:
        """
        Transcribes audio using Whisper and creates modern viral-style ASS subtitles.
        Returns: (output_ass_path, transcript_text)
        """
        model = self._get_model()
        print(f"[SubtitleGenerator] Transcribing {audio_or_video_path}...")
        result = model.transcribe(
            audio_or_video_path,
            word_timestamps=True,
            fp16=False
        )

        segments = result.get("segments", [])
        full_transcript = result.get("text", "").strip()

        # ASS file header configured for 1080x1920 portrait
        ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralYellow, Arial, 52, &H0000F7FF, &H000000FF, &H00000000, &H00000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 4, 2, 2, 60, 60, 440, 1
Style: ViralWhite, Arial, 52, &H00FFFFFF, &H000000FF, &H00000000, &H00000000, 1, 0, 0, 0, 100, 100, 1, 0, 1, 4, 2, 2, 60, 60, 440, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        # Break segments down into punchy 3-5 word bursts (Alex Hormozi style)
        for seg in segments:
            words = seg.get("words", [])
            if words:
                # Group words into chunks
                for i in range(0, len(words), max_words_per_line):
                    chunk = words[i:i + max_words_per_line]
                    if not chunk:
                        continue
                    start_t = chunk[0].get("start", seg.get("start", 0))
                    end_t = chunk[-1].get("end", seg.get("end", start_t + 1))
                    
                    # Ensure positive duration
                    if end_t <= start_t:
                        end_t = start_t + 0.8

                    chunk_text = " ".join(w.get("word", "").strip() for w in chunk).strip()
                    if not chunk_text:
                        continue

                    # Alternating yellow and white for dynamic viral feel
                    style = "ViralYellow" if (len(events) % 2 == 0) else "ViralWhite"
                    start_str = self._format_timestamp(start_t)
                    end_str = self._format_timestamp(end_t)
                    events.append(f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{chunk_text.upper()}")
            else:
                # Fallback to segment text if words not broken down
                start_t = seg.get("start", 0)
                end_t = seg.get("end", start_t + 2)
                text = seg.get("text", "").strip().upper()
                if text:
                    start_str = self._format_timestamp(start_t)
                    end_str = self._format_timestamp(end_t)
                    events.append(f"Dialogue: 0,{start_str},{end_str},ViralYellow,,0,0,0,,{text}")

        os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events) + "\n")

        print(f"[SubtitleGenerator] Generated ASS subtitles ({len(events)} lines) -> {output_ass_path}")
        return output_ass_path, full_transcript
