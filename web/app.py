import os
import uuid
import threading
import subprocess
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.downloader.yt import YouTubeDownloader
from core.analyzer.audio_spike import AudioSpikeAnalyzer
from core.layout.gaming_layout import GamingLayoutDetector
from core.layout.podcast_layout import PodcastLayoutDetector
from core.layout.talking_head_layout import TalkingHeadLayoutDetector
from core.renderer.clipper import VideoClipper
from core.subtitles.sub_generator import SubtitleGenerator
from core.ai.copywriter import AICopywriter

app = FastAPI(title="AI Multi-Mode Auto-Clipper 9:16 (Ultimate 24h Edition)")

# In-memory task registry
TASKS: Dict[str, Dict[str, Any]] = {}

class ClipRequest(BaseModel):
    source: str
    mode: str = "gaming" # gaming, podcast, talking_head
    start_min: float = 0.0
    duration_min: float = 60.0
    clip_len: int = 30
    top_k: int = 2
    hook_title: str = ""
    layout: str = "auto" # auto, split, portrait, blur
    generate_subtitles: bool = True
    whisper_model: str = "base" # tiny, base, small
    generate_copywriting: bool = True

def run_pipeline(task_id: str, req: ClipRequest):
    task = TASKS[task_id]
    logs = task["logs"]
    
    def log(msg: str):
        logs.append(msg)
        print(f"[{task_id}] {msg}")

    try:
        downloader = YouTubeDownloader(output_dir="downloads")
        analyzer = AudioSpikeAnalyzer()
        clipper = VideoClipper(output_dir="output")
        copywriter = AICopywriter()

        mode_titles = {
            "gaming": "🎮 Mode Gaming (Audio Spike & Facecam Split)",
            "podcast": "🎙️ Mode Podcast / Interview (Dual Speaker Split)",
            "talking_head": "🗣️ Mode Talking Head (Auto-Reframe 9:16)"
        }
        log(f"⚡ Mode Aktif: {mode_titles.get(req.mode, req.mode)}")

        default_hooks = {
            "gaming": "GTA VI MOMENT 💀",
            "podcast": "DEEP TALK MOMENT 🎙️",
            "talking_head": "TIPS PENTING WAJIB TAHU 💡"
        }
        hook_title = req.hook_title.strip() if req.hook_title else default_hooks.get(req.mode, "VIRAL MOMENT 🔥")

        start_sec = int(req.start_min * 60)
        dur_sec = int(req.duration_min * 60)
        is_youtube = req.source.startswith("http://") or req.source.startswith("https://")
        total_sec = 0

        if is_youtube:
            log(f"[1/4] 🌐 Mengambil info YouTube...")
            info = downloader.get_info(req.source)
            title = info.get("title", "Video")
            total_sec = int(info.get("duration", 0))
            log(f"       Judul   : {title}")
            log(f"       Total Durasi: {total_sec // 3600} jam {(total_sec % 3600) // 60} menit {total_sec % 60} detik")
            
            # If user asks for more than available or full stream, clamp to total duration
            if dur_sec <= 0 or (start_sec + dur_sec) > total_sec:
                dur_sec = max(60, total_sec - start_sec)

        rendered_clips = []
        sub_generator = SubtitleGenerator(model_name=req.whisper_model) if req.generate_subtitles else None

        # STRATEGY A: For Long Video Windows (> 20 Minutes / Full Livestream)
        # Use Smart Audio-First Slicing: Scan audio across the 23 hours in seconds,
        # find the exact top moments, then download only the HD video clips for those moments!
        if is_youtube and dur_sec > 1200:
            log(f"\n[1/4] ⚡ Mengaktifkan Smart Audio-First Scan untuk Livestream Panjang ({dur_sec // 3600}j {(dur_sec % 3600) // 60}m)...")
            log(f"       Mengunduh stream audio super cepat untuk memindai seluruh durasi...")
            audio_file = downloader.download_audio_stream(
                url=req.source,
                start_sec=start_sec,
                end_sec=start_sec + dur_sec,
                output_filename=f"audio_{task_id[:8]}.m4a"
            )

            log(f"\n[2/4] 🔊 Memindai puncak energi suara di sepanjang durasi tersebut...")
            highlights = analyzer.analyze_highlights(
                audio_file,
                clip_duration=req.clip_len,
                top_k=req.top_k,
                mode=req.mode
            )
            log(f"       Ditemukan {len(highlights)} momen terbaik di seluruh video:")
            for idx, h in enumerate(highlights, 1):
                abs_time = start_sec + h["start"]
                log(f"       #{idx}: Jam {int(abs_time // 3600):02d}:{int((abs_time % 3600) // 60):02d}:{int(abs_time % 60):02d} (Skor: {h['score']})")

            # Process each highlight
            log(f"\n[3/4 & 4/4] 🎬 Mengunduh video HD per segmen & merender 9:16 Shorts...")
            for idx, h in enumerate(highlights, 1):
                abs_start = max(0, int(start_sec + h["start"]))
                abs_end = abs_start + req.clip_len
                time_label = f"{int(abs_start // 3600):02d}h{int((abs_start % 3600) // 60):02d}m{int(abs_start % 60):02d}s"
                
                log(f"\n--- Memproses Klip #{idx} (pada menit ke-{abs_start // 60}) ---")
                clip_video = downloader.download_segment(
                    url=req.source,
                    start_sec=abs_start,
                    end_sec=abs_end,
                    output_filename=f"seg_{task_id[:6]}_{idx}.mp4"
                )

                # Layout Detection on this clip
                selected_layout, layout_data = detect_layout_for_mode(req.mode, clip_video, req.layout, log)

                # Subtitles
                sub_ass_path, transcript_text = process_clip_subtitles(
                    sub_generator, clip_video, req.whisper_model, task_id, idx, log
                )

                # Copywriting
                social_pack = copywriter.generate_social_pack(
                    transcript=transcript_text,
                    mode=req.mode,
                    hook_title=f"{hook_title} ({time_label})"
                ) if req.generate_copywriting else None

                # Render final short
                out_filename = f"{req.mode}_{task_id[:6]}_{idx}.mp4"
                log(f"       Merender Klip 9:16 #{idx}...")
                clipper.render_clip(
                    input_video=clip_video,
                    start_sec=0, # Already cut to duration
                    duration=req.clip_len,
                    output_name=out_filename,
                    layout_mode=selected_layout,
                    layout_data=layout_data,
                    hook_title=hook_title,
                    mode=req.mode,
                    subtitle_ass_path=sub_ass_path
                )

                rendered_clips.append({
                    "filename": out_filename,
                    "url": f"/output/{out_filename}",
                    "duration": req.clip_len,
                    "mode": req.mode,
                    "transcript": transcript_text,
                    "social_pack": social_pack
                })
                log(f"       ✅ Klip #{idx} selesai!")

        # STRATEGY B: For Moderate / Short Slices (< 20 Minutes) or Local File
        else:
            video_file = req.source
            if is_youtube:
                log(f"       Mengunduh sampel video ({req.start_min:.1f}m - {req.start_min + req.duration_min:.1f}m)...")
                video_file = downloader.download_segment(
                    url=req.source,
                    start_sec=start_sec,
                    end_sec=start_sec + dur_sec,
                    output_filename=f"{req.mode}_{task_id[:8]}.mp4"
                )

            log(f"\n[2/4] 🔊 Menganalisis highlight audio untuk mode [{req.mode.upper()}]...")
            highlights = analyzer.analyze_highlights(
                video_file,
                clip_duration=req.clip_len,
                top_k=req.top_k,
                mode=req.mode
            )
            log(f"       Ditemukan {len(highlights)} momen terbaik:")
            for idx, h in enumerate(highlights, 1):
                log(f"       #{idx}: {h['start']}s - {h['end']}s (Puncak di {h['spike_time']}s | Skor: {h['score']})")

            selected_layout, layout_data = detect_layout_for_mode(req.mode, video_file, req.layout, log)

            for idx, h in enumerate(highlights, 1):
                out_filename = f"{req.mode}_{task_id[:6]}_{idx}.mp4"
                clip_wav = os.path.join("downloads", f"audio_{task_id[:6]}_{idx}.wav")
                extract_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(h["start"]),
                    "-t", str(req.clip_len),
                    "-i", video_file,
                    "-vn", "-ac", "1", "-ar", "16000",
                    clip_wav
                ]
                subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                sub_ass_path, transcript_text = process_clip_subtitles(
                    sub_generator, clip_wav, req.whisper_model, task_id, idx, log
                )
                if os.path.exists(clip_wav):
                    try: os.remove(clip_wav)
                    except Exception: pass

                social_pack = copywriter.generate_social_pack(
                    transcript=transcript_text,
                    mode=req.mode,
                    hook_title=hook_title
                ) if req.generate_copywriting else None

                log(f"       Merender Klip #{idx} ({req.clip_len}s)...")
                clipper.render_clip(
                    input_video=video_file,
                    start_sec=h["start"],
                    duration=req.clip_len,
                    output_name=out_filename,
                    layout_mode=selected_layout,
                    layout_data=layout_data,
                    hook_title=hook_title,
                    mode=req.mode,
                    subtitle_ass_path=sub_ass_path
                )

                rendered_clips.append({
                    "filename": out_filename,
                    "url": f"/output/{out_filename}",
                    "duration": req.clip_len,
                    "mode": req.mode,
                    "transcript": transcript_text,
                    "social_pack": social_pack
                })
                log(f"       ✅ Klip #{idx} selesai!")

        task["status"] = "done"
        task["clips"] = rendered_clips
        log("\n🎉 Seluruh klip siap ditonton dan diunduh beserta copywriting medsos!")

    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        log(f"\n❌ Error: {e}")

def detect_layout_for_mode(mode: str, video_path: str, layout_pref: str, log_fn):
    selected_layout = "blurred_bg"
    layout_data = None

    if layout_pref == "blur":
        selected_layout = "blurred_bg"
        log_fn("       Layout dipilih: Cinematic Blurred Background")
    elif mode == "gaming":
        detector = GamingLayoutDetector()
        facecam = detector.detect_streamer_facecam(video_path)
        if facecam and (layout_pref in ["auto", "split"]):
            selected_layout = "facecam_split"
            layout_data = facecam
            log_fn(f"       Facecam streamer terdeteksi: x={facecam['x']}, y={facecam['y']}, size={facecam['w']}x{facecam['h']}")
            log_fn("       Layout: Split Screen (Atas: Streamer, Bawah: Gameplay)")
        else:
            selected_layout = "blurred_bg"
            log_fn("       Facecam tidak terdeteksi. Menggunakan layout Blurred Background.")
    elif mode == "podcast":
        detector = PodcastLayoutDetector()
        speakers = detector.detect_podcast_speakers(video_path)
        if speakers and (layout_pref in ["auto", "split"]):
            selected_layout = "podcast_split"
            layout_data = speakers
            log_fn("       Speaker podcast ditemukan (Host & Guest)!")
            log_fn("       Layout: Dual Speaker Split Screen")
        else:
            selected_layout = "blurred_bg"
            log_fn("       Menggunakan layout Blurred Background.")
    elif mode == "talking_head":
        detector = TalkingHeadLayoutDetector()
        head_box = detector.detect_talking_head(video_path)
        if head_box and (layout_pref in ["auto", "portrait"]):
            selected_layout = "talking_head"
            layout_data = head_box
            log_fn("       Layout: 9:16 Portrait Auto-Reframe")
        else:
            selected_layout = "blurred_bg"
            log_fn("       Menggunakan layout Blurred Background.")

    return selected_layout, layout_data

def process_clip_subtitles(sub_gen, media_path, whisper_model, task_id, idx, log_fn):
    if not sub_gen:
        return None, ""
    try:
        log_fn(f"       🎙️ Menjalankan Whisper AI Subtitles ({whisper_model})...")
        ass_file = os.path.join("output", f"sub_{task_id[:6]}_{idx}.ass")
        sub_ass_path, transcript_text = sub_gen.generate_subtitles(media_path, ass_file)
        log_fn(f"       ✨ Subtitle animasi siap ({len(transcript_text.split())} kata)")
        return sub_ass_path, transcript_text
    except Exception as e:
        log_fn(f"       ⚠️ Subtitle warning: {e}. Melanjutkan tanpa subtitle...")
        return None, ""

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/clip")
def start_clipping(req: ClipRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        "status": "running",
        "logs": ["Memulai proses clipping..."],
        "clips": [],
        "error": None
    }
    background_tasks.add_task(run_pipeline, task_id, req)
    return {"status": "ok", "task_id": task_id}

@app.get("/api/status/{task_id}")
def get_task_status(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id]

@app.get("/api/existing-clips")
def get_existing_clips():
    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    clips = []
    for f in sorted(os.listdir(out_dir), reverse=True):
        if f.endswith(".mp4"):
            clips.append({
                "filename": f,
                "url": f"/output/{f}",
                "duration": 30
            })
    return {"clips": clips}

@app.get("/output/{filename}")
def serve_output(filename: str):
    file_path = os.path.join("output", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=False)
