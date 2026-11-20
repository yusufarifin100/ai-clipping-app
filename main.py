import os
import sys
import argparse
from core.downloader.yt import YouTubeDownloader
from core.analyzer.audio_spike import AudioSpikeAnalyzer
from core.layout.gaming_layout import GamingLayoutDetector
from core.renderer.clipper import VideoClipper

def process_gaming_video(
    source: str,
    time_window_start: int = 0,
    time_window_duration: int = 300, # 5 minutes default sample for testing long streams
    clip_duration: int = 30,
    top_k: int = 2,
    layout_preference: str = "auto", # auto, facecam, or blur
    hook_title: str = "GTA VI MOMENT 💀"
):
    print("=" * 60)
    print("🎮 AI GAMING CLIPPING PIPELINE")
    print("=" * 60)

    downloader = YouTubeDownloader(output_dir="downloads")
    analyzer = AudioSpikeAnalyzer()
    layout_detector = GamingLayoutDetector()
    clipper = VideoClipper(output_dir="output")

    video_file = source

    # 1. Download if URL
    if source.startswith("http://") or source.startswith("https://"):
        print(f"\n[1/4] 🌐 Checking YouTube URL: {source}")
        info = downloader.get_info(source)
        title = info.get("title", "Video")
        total_sec = info.get("duration", 0)
        print(f"       Title   : {title}")
        print(f"       Duration: {total_sec // 3600}h {(total_sec % 3600) // 60}m {total_sec % 60}s")

        # For long livestreams (> 15 minutes), download slice to save time & bandwidth
        if total_sec > 900 and time_window_duration > 0:
            print(f"       [Notice] Video is long ({total_sec // 3600}h). Downloading test slice of {time_window_duration}s...")
            video_file = downloader.download_segment(
                url=source,
                start_sec=time_window_start,
                end_sec=time_window_start + time_window_duration,
                output_filename="stream_sample.mp4"
            )
        else:
            print("       Downloading video...")
            video_file = downloader.download_full(source, output_filename="stream_full.mp4")

    if not os.path.exists(video_file):
        print(f"❌ Error: Video file not found: {video_file}")
        return

    # 2. Analyze Audio Spikes
    print(f"\n[2/4] 🔊 Analyzing Audio Spikes (Peak Excitement Moments)...")
    highlights = analyzer.analyze_highlights(video_file, clip_duration=clip_duration, top_k=top_k)
    print(f"       Found {len(highlights)} peak highlight moment(s):")
    for i, h in enumerate(highlights, 1):
        print(f"       #{i}: {h['start']}s - {h['end']}s (Peak at {h['spike_time']}s | Excitement Score: {h['score']})")

    # 3. Detect Facecam & Select Layout
    print(f"\n[3/4] 📹 Analyzing Screen Layout (Facecam Detection)...")
    facecam_box = layout_detector.detect_streamer_facecam(video_file)

    selected_layout = "blurred_bg"
    if layout_preference == "facecam" or (layout_preference == "auto" and facecam_box):
        if facecam_box:
            selected_layout = "facecam_split"
            print(f"       Facecam detected at: x={facecam_box['x']}, y={facecam_box['y']}, size={facecam_box['w']}x{facecam_box['h']}")
            print("       Layout selected: Split Screen (Top: Streamer, Bottom: Gameplay)")
        else:
            print("       No streamer facecam detected. Using: Blurred Background Layout")
    else:
        print("       Layout selected: Cinematic Blurred Background")

    # 4. Render Final Vertical Shorts (9:16)
    print(f"\n[4/4] 🎬 Rendering 9:16 Shorts to 'output/' folder...")
    rendered_files = []
    for i, h in enumerate(highlights, 1):
        out_name = f"short_clip_{i}.mp4"
        out_path = clipper.render_clip(
            input_video=video_file,
            start_sec=h["start"],
            duration=clip_duration,
            output_name=out_name,
            layout_mode=selected_layout,
            facecam_box=facecam_box,
            hook_title=hook_title
        )
        rendered_files.append(out_path)
        print(f"       ✅ Clip #{i} saved: {out_path}")

    print("\n" + "=" * 60)
    print(f"🎉 SUKSES! {len(rendered_files)} video shorts vertikal siap diupload:")
    for f in rendered_files:
        print(f"   -> {os.path.abspath(f)}")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Gaming Clipping App")
    parser.add_argument("source", help="YouTube URL or local MP4 path")
    parser.add_argument("--start", type=int, default=120, help="Start time in seconds for analysis window (default: 120s)")
    parser.add_argument("--duration", type=int, default=180, help="Duration in seconds of window to analyze (default: 180s)")
    parser.add_argument("--clip-len", type=int, default=25, help="Length of each output short in seconds (default: 25s)")
    parser.add_argument("--top", type=int, default=1, help="Number of clips to generate (default: 1)")
    parser.add_argument("--layout", choices=["auto", "facecam", "blur"], default="auto", help="Layout style")
    parser.add_argument("--hook", default="GTA VI MOMENT 💀", help="Hook title banner text")

    args = parser.parse_args()

    process_gaming_video(
        source=args.source,
        time_window_start=args.start,
        time_window_duration=args.duration,
        clip_duration=args.clip_len,
        top_k=args.top,
        layout_preference=args.layout,
        hook_title=args.hook
    )
