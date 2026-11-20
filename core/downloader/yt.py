import os
import subprocess
from typing import Optional, Dict

class YouTubeDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_info(self, url: str) -> Dict[str, any]:
        """Fetch title and duration without downloading."""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android,web",
            url
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"Failed to fetch video info: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "duration": data.get("duration", 0), # in seconds
            "thumbnail": data.get("thumbnail")
        }

    def download_audio_stream(
        self,
        url: str,
        start_sec: int = 0,
        end_sec: Optional[int] = None,
        output_filename: Optional[str] = None
    ) -> str:
        """Download fast lightweight audio stream for full livestream scanning."""
        if not output_filename:
            output_filename = "stream_audio.m4a"
        output_path = os.path.join(self.output_dir, output_filename)

        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "-f", "bestaudio[ext=m4a]/bestaudio/140/ba/b",
            "-o", output_path,
            "--force-overwrites"
        ]

        if start_sec > 0 or (end_sec and end_sec > 0):
            start_time_str = f"{start_sec // 3600:02d}:{(start_sec % 3600) // 60:02d}:{start_sec % 60:02d}"
            end_time_str = f"{end_sec // 3600:02d}:{(end_sec % 3600) // 60:02d}:{end_sec % 60:02d}" if end_sec else "inf"
            section = f"*{start_time_str}-{end_time_str}"
            cmd.extend(["--download-sections", section])

        cmd.append(url)
        print(f"[Downloader] Downloading audio stream ({output_filename})...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            # Fallback format
            cmd[4] = "ba/b"
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Audio download failed: {result.stderr}")

        return output_path

    def download_segment(self, url: str, start_sec: int, end_sec: int, output_filename: Optional[str] = None) -> str:
        """Download a specific time range to save bandwidth and storage."""
        if not output_filename:
            output_filename = f"segment_{start_sec}_{end_sec}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        start_time_str = f"{start_sec // 3600:02d}:{(start_sec % 3600) // 60:02d}:{start_sec % 60:02d}"
        end_time_str = f"{end_sec // 3600:02d}:{(end_sec % 3600) // 60:02d}:{end_sec % 60:02d}"
        section = f"*{start_time_str}-{end_time_str}"

        cmd = [
            "yt-dlp",
            "--download-sections", section,
            "--extractor-args", "youtube:player_client=android,web",
            "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--force-overwrites",
            url
        ]

        print(f"[Downloader] Downloading section {start_time_str} to {end_time_str}...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            print("[Downloader] Primary stream failed, trying fallback stream...")
            fallback_cmd = [
                "yt-dlp",
                "--download-sections", section,
                "--extractor-args", "youtube:player_client=android,web",
                "-f", "best",
                "-o", output_path,
                "--force-overwrites",
                url
            ]
            result = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Download failed: {result.stderr}")

        return output_path

    def download_full(self, url: str, max_height: int = 720, output_filename: Optional[str] = None) -> str:
        """Download full video."""
        if not output_filename:
            output_filename = "downloaded_video.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--force-overwrites",
            url
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode != 0:
            fallback_cmd = [
                "yt-dlp",
                "--extractor-args", "youtube:player_client=android,web",
                "-f", "best",
                "-o", output_path,
                "--force-overwrites",
                url
            ]
            result = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
            if result.returncode != 0:
                raise RuntimeError(f"Download failed: {result.stderr}")

        return output_path
