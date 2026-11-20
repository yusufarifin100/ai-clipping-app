import os
import subprocess
from typing import Optional, Dict

class VideoClipper:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def render_clip(
        self,
        input_video: str,
        start_sec: float,
        duration: float,
        output_name: str,
        layout_mode: str = "blurred_bg", # "blurred_bg" or "facecam_split"
        facecam_box: Optional[Dict[str, int]] = None,
        hook_title: Optional[str] = "GTA VI MOMENT 💀"
    ) -> str:
        """
        Renders a 9:16 vertical short (1080x1920) with selected layout and hook text.
        """
        output_path = os.path.join(self.output_dir, output_name)

        if layout_mode == "facecam_split" and facecam_box:
            # Split screen layout: Top 720px Webcam, Bottom 1200px Gameplay
            fx, fy, fw, fh = facecam_box["x"], facecam_box["y"], facecam_box["w"], facecam_box["h"]
            
            filter_str = (
                f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720[cam];"
                f"[0:v]scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200[game];"
                f"[cam][game]vstack=inputs=2[stacked];"
                # Draw separating neon bar (color cyan/magenta) and hook banner
                f"[stacked]drawbox=y=716:color=0x00F0FF@1:width=1080:height=8:t=fill[v_bar];"
                f"[v_bar]drawbox=y=700:color=black@0.65:width=1080:height=75:t=fill,"
                f"drawtext=text='{hook_title}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=720:shadowcolor=black:shadowx=2:shadowy=2[v]"
            )
        else:
            # Blurred background layout: 16:9 gameplay centered in 9:16 frame
            filter_str = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                "[0:v]scale=1080:-1[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[merged];"
                f"[merged]drawbox=y=220:color=black@0.65:width=1080:height=85:t=fill,"
                f"drawbox=y=305:color=0x00F0FF@1:width=1080:height=4:t=fill,"
                f"drawtext=text='{hook_title}':fontcolor=yellow:fontsize=46:x=(w-text_w)/2:y=240:shadowcolor=black:shadowx=3:shadowy=3[v]"
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

        print(f"[Renderer] Rendering clip to {output_path}...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            # Fallback if drawtext fails (e.g. font missing on Windows)
            print("[Renderer] Drawtext warning, retrying with simplified filter...")
            if layout_mode == "facecam_split" and facecam_box:
                simple_filter = (
                    f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale=1080:720:force_original_aspect_ratio=increase,crop=1080:720[cam];"
                    f"[0:v]scale=1080:1200:force_original_aspect_ratio=increase,crop=1080:1200[game];"
                    f"[cam][game]vstack=inputs=2[v]"
                )
            else:
                simple_filter = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                    "[0:v]scale=1080:-1[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
                )
            cmd[cmd.index(filter_str)] = simple_filter
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Rendering failed: {result.stderr}")

        return output_path
