import os
import subprocess
from typing import Optional, Dict, Any

class VideoClipper:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _sanitize_title(self, text: str) -> str:
        """Escape special characters for ffmpeg drawtext."""
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "%%")

    def render_clip(
        self,
        input_video: str,
        start_sec: float,
        duration: float,
        output_name: str,
        layout_mode: str = "blurred_bg", # "facecam_split", "podcast_split", "talking_head", "blurred_bg"
        layout_data: Optional[Dict[str, Any]] = None,
        hook_title: Optional[str] = "VIRAL MOMENT 🔥",
        mode: str = "gaming",
        subtitle_ass_path: Optional[str] = None
    ) -> str:
        """
        Renders a 9:16 vertical short (1080x1920) customized for Gaming, Podcast, or Talking Head,
        with optional dynamic animated subtitles burned in.
        """
        output_path = os.path.join(self.output_dir, output_name)
        safe_title = self._sanitize_title(hook_title or "")

        # Format subtitle filter if ASS file exists
        sub_filter = ""
        if subtitle_ass_path and os.path.exists(subtitle_ass_path):
            rel_sub = os.path.relpath(subtitle_ass_path).replace("\\", "/").replace(":", "\\:")
            sub_filter = f",subtitles='{rel_sub}'"

        # 1. Gaming Facecam Split Layout
        if layout_mode == "facecam_split" and layout_data:
            fx, fy, fw, fh = layout_data["x"], layout_data["y"], layout_data["w"], layout_data["h"]
            filter_str = (
                f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720[cam];"
                f"[0:v]scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200[game];"
                f"[cam][game]vstack=inputs=2[stacked];"
                f"[stacked]drawbox=y=716:color=0x00F0FF@1:width=1080:height=8:t=fill[v_bar];"
                f"[v_bar]drawbox=y=700:color=black@0.65:width=1080:height=75:t=fill,"
                f"drawtext=text='{safe_title}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=720:shadowcolor=black:shadowx=2:shadowy=2"
                f"{sub_filter}[v]"
            )
            simple_filter = (
                f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720[cam];"
                f"[0:v]scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200[game];"
                f"[cam][game]vstack=inputs=2[v]"
            )

        # 2. Podcast Dual Speaker Split Layout
        elif layout_mode == "podcast_split" and layout_data and "speaker_left" in layout_data:
            s1 = layout_data["speaker_left"]
            s2 = layout_data["speaker_right"]
            filter_str = (
                f"[0:v]crop={s1['w']}:{s1['h']}:{s1['x']}:{s1['y']},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[s1];"
                f"[0:v]crop={s2['w']}:{s2['h']}:{s2['x']}:{s2['y']},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[s2];"
                f"[s1][s2]vstack=inputs=2[stacked];"
                f"[stacked]drawbox=y=956:color=0xF59E0B@1:width=1080:height=8:t=fill[v_bar];"
                f"[v_bar]drawbox=y=926:color=black@0.75:width=1080:height=68:t=fill,"
                f"drawtext=text='{safe_title}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=942:shadowcolor=black:shadowx=2:shadowy=2"
                f"{sub_filter}[v]"
            )
            simple_filter = (
                f"[0:v]crop={s1['w']}:{s1['h']}:{s1['x']}:{s1['y']},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[s1];"
                f"[0:v]crop={s2['w']}:{s2['h']}:{s2['x']}:{s2['y']},scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[s2];"
                f"[s1][s2]vstack=inputs=2[v]"
            )

        # 3. Solo Talking Head Auto-Reframe (9:16 Center Portrait)
        elif layout_mode == "talking_head" and layout_data:
            cx, cy, cw, ch = layout_data["x"], layout_data["y"], layout_data["w"], layout_data["h"]
            filter_str = (
                f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale=1080:1920[reframe];"
                f"[reframe]drawbox=y=160:color=black@0.65:width=1080:height=85:t=fill,"
                f"drawbox=y=242:color=0x38BDF8@1:width=1080:height=4:t=fill,"
                f"drawtext=text='{safe_title}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=180:shadowcolor=black:shadowx=2:shadowy=2"
                f"{sub_filter}[v]"
            )
            simple_filter = f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale=1080:1920[v]"

        # 4. Fallback: Cinematic Blurred Background Layout
        else:
            filter_str = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                "[0:v]scale=1080:-1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
                f"[merged]drawbox=y=220:color=black@0.65:width=1080:height=85:t=fill,"
                f"drawbox=y=305:color=0x00F0FF@1:width=1080:height=4:t=fill,"
                f"drawtext=text='{safe_title}':fontcolor=yellow:fontsize=46:x=(w-text_w)/2:y=240:shadowcolor=black:shadowx=3:shadowy=3"
                f"{sub_filter}[v]"
            )
            simple_filter = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                "[0:v]scale=1080:-1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
            )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-t", str(duration),
            "-i", input_video,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            output_path
        ]

        sub_msg = f" with animated subtitles ({subtitle_ass_path})" if sub_filter else ""
        print(f"[Renderer] Rendering {layout_mode} ({mode}){sub_msg} -> {output_path}...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            print("[Renderer] Warning with complex filter/subtitles, retrying with simplified filter...")
            cmd[cmd.index(filter_str)] = simple_filter
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Rendering failed: {result.stderr}")

        return output_path
