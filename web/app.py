import os
import uuid
import threading
from typing import Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.downloader.yt import YouTubeDownloader
from core.analyzer.audio_spike import AudioSpikeAnalyzer
from core.layout.gaming_layout import GamingLayoutDetector
from core.renderer.clipper import VideoClipper

app = FastAPI(title="AI Gaming Clipper 9:16")

# In-memory task registry
TASKS: Dict[str, Dict] = {}

class ClipRequest(BaseModel):
    source: str
    start_min: float = 5.0
    duration_min: float = 3.0
    clip_len: int = 30
    top_k: int = 2
    hook_title: str = "GTA VI MOMENT 💀"
    layout: str = "auto" # auto, facecam, blur

def run_pipeline(task_id: str, req: ClipRequest):
    task = TASKS[task_id]
    logs = task["logs"]
    
    def log(msg: str):
        logs.append(msg)
        print(f"[{task_id}] {msg}")

    try:
        downloader = YouTubeDownloader(output_dir="downloads")
        analyzer = AudioSpikeAnalyzer()
        layout_detector = GamingLayoutDetector()
        clipper = VideoClipper(output_dir="output")

        video_file = req.source
        start_sec = int(req.start_min * 60)
        dur_sec = int(req.duration_min * 60)

        # 1. Download if URL
        if req.source.startswith("http://") or req.source.startswith("https://"):
            log(f"[1/4] 🌐 Mengambil info YouTube...")
            info = downloader.get_info(req.source)
            title = info.get("title", "Video")
            total_sec = info.get("duration", 0)
            log(f"       Judul   : {title}")
            log(f"       Total Durasi: {total_sec // 3600} jam {(total_sec % 3600) // 60} menit")

            if total_sec > 900 and dur_sec > 0:
                log(f"       Mengunduh slice {req.start_min:.1f}m s/d {req.start_min + req.duration_min:.1f}m...")
                video_file = downloader.download_segment(
                    url=req.source,
                    start_sec=start_sec,
                    end_sec=start_sec + dur_sec,
                    output_filename=f"stream_{task_id[:8]}.mp4"
                )
            else:
                log("       Mengunduh video lengkap...")
                video_file = downloader.download_full(req.source, output_filename=f"video_{task_id[:8]}.mp4")

        # 2. Audio Spike Analysis
        log("\n[2/4] 🔊 Menganalisis gelombang desibel (Audio Peak Detection)...")
        highlights = analyzer.analyze_highlights(video_file, clip_duration=req.clip_len, top_k=req.top_k)
        log(f"       Ditemukan {len(highlights)} momen klimaks:")
        for idx, h in enumerate(highlights, 1):
            log(f"       #{idx}: {h['start']}s - {h['end']}s (Puncak di {h['spike_time']}s | Skor: {h['score']})")

        # 3. Facecam Layout
        log("\n[3/4] 📹 Memeriksa Facecam Streamer...")
        facecam_box = layout_detector.detect_streamer_facecam(video_file)
        
        layout_mode = "blurred_bg"
        if req.layout == "facecam" or (req.layout == "auto" and facecam_box):
            if facecam_box:
                layout_mode = "facecam_split"
                log(f"       Facecam terdeteksi di: x={facecam_box['x']}, y={facecam_box['y']}")
                log("       Layout: Split Screen (Atas: Streamer, Bawah: Gameplay)")
            else:
                log("       Tidak ada facecam terdeteksi. Menggunakan layout Blurred Background.")
        else:
            log("       Layout: Cinematic Blurred Background.")

        # 4. Rendering
        log("\n[4/4] 🎬 Merender video vertikal 9:16 (1080x1920)...")
        rendered_clips = []
        for idx, h in enumerate(highlights, 1):
            out_filename = f"short_{task_id[:6]}_{idx}.mp4"
            log(f"       Merender Klip #{idx} ({req.clip_len}s)...")
            out_path = clipper.render_clip(
                input_video=video_file,
                start_sec=h["start"],
                duration=req.clip_len,
                output_name=out_filename,
                layout_mode=layout_mode,
                facecam_box=facecam_box,
                hook_title=req.hook_title
            )
            rendered_clips.append({
                "filename": out_filename,
                "url": f"/output/{out_filename}",
                "duration": req.clip_len
            })
            log(f"       ✅ Klip #{idx} selesai!")

        task["status"] = "done"
        task["clips"] = rendered_clips
        log("\n🎉 Seluruh klip siap ditonton dan diunduh!")

    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        log(f"\n❌ Error fatal: {e}")

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
    for f in os.listdir(out_dir):
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
