import os
import sys
import argparse
import subprocess
from core.downloader.yt import YouTubeDownloader
from core.analyzer.audio_spike import AudioSpikeAnalyzer
from core.layout.gaming_layout import GamingLayoutDetector
from core.layout.podcast_layout import PodcastLayoutDetector
from core.layout.talking_head_layout import TalkingHeadLayoutDetector
from core.renderer.clipper import VideoClipper
from core.subtitles.sub_generator import SubtitleGenerator
from core.ai.copywriter import AICopywriter

def process_video(
    source: str,
    mode: str = "gaming",
    time_window_start: int = 0,
    time_window_duration: int = 300,
    clip_duration: int = 30,
    top_k: int = 2,
    layout_preference: str = "auto",
    hook_title: str = None,
    generate_subtitles: bool = True,
    whisper_model: str = "base"
):
    mode_names = {
        "gaming": "🎮 AI GAMING AUTO-CLIPPER",
        "podcast": "🎙️ AI PODCAST & INTERVIEW AUTO-CLIPPER",
        "talking_head": "🗣️ AI TALKING HEAD & COMMENTARY AUTO-CLIPPER"
    }

    default_hooks = {
        "gaming": "GTA VI MOMENT 💀",
        "podcast": "DEEP TALK MOMENT 🎙️",
        "talking_head": "TIPS PENTING WAJIB TAHU 💡"
    }

    if not hook_title:
        hook_title = default_hooks.get(mode, "VIRAL MOMENT 🔥")

    print("=" * 65)
    print(mode_names.get(mode, "🎬 AI MULTI-MODE VIDEO CLIPPER"))
    print("=" * 65)

    downloader = YouTubeDownloader(output_dir="downloads")
    analyzer = AudioSpikeAnalyzer()
    clipper = VideoClipper(output_dir="output")
    copywriter = AICopywriter()

    video_file = source

    # 1. Download if URL
    if source.startswith("http://") or source.startswith("https://"):
        print(f"\n[1/4] 🌐 Checking YouTube URL: {source}")
        info = downloader.get_info(source)
        title = info.get("title", "Video")
        total_sec = info.get("duration", 0)
        print(f"       Title   : {title}")
        print(f"       Duration: {total_sec // 3600}h {(total_sec % 3600) // 60}m {total_sec % 60}s")

        if total_sec > 900 and time_window_duration > 0:
            print(f"       [Notice] Video is long ({total_sec // 3600}h). Downloading segment ({time_window_start}s to {time_window_start + time_window_duration}s)...")
            video_file = downloader.download_segment(
                url=source,
                start_sec=time_window_start,
                end_sec=time_window_start + time_window_duration,
                output_filename=f"{mode}_sample.mp4"
            )
        else:
            print("       Downloading full video...")
            video_file = downloader.download_full(source, output_filename=f"{mode}_full.mp4")

    if not os.path.exists(video_file):
        print(f"❌ Error: Video file not found: {video_file}")
        return

    # 2. Analyze Audio Highlights
    print(f"\n[2/4] 🔊 Analyzing Audio Highlights (Mode: {mode.upper()})...")
    highlights = analyzer.analyze_highlights(
        video_file,
        clip_duration=clip_duration,
        top_k=top_k,
        mode=mode
    )
    print(f"       Found {len(highlights)} peak moment(s):")
    for i, h in enumerate(highlights, 1):
        print(f"       #{i}: {h['start']}s - {h['end']}s (Spike at {h['spike_time']}s | Score: {h['score']})")

    # 3. Detect Layout based on Mode
    print(f"\n[3/4] 📹 Analyzing Screen Layout (Mode: {mode.upper()})...")
    selected_layout = "blurred_bg"
    layout_data = None

    if layout_preference == "blur":
        selected_layout = "blurred_bg"
        print("       Layout selected by user preference: Cinematic Blurred Background")
    elif mode == "gaming":
        detector = GamingLayoutDetector()
        facecam_box = detector.detect_streamer_facecam(video_file)
        if facecam_box and (layout_preference == "auto" or layout_preference == "split"):
            selected_layout = "facecam_split"
            layout_data = facecam_box
            print(f"       Streamer facecam detected at: x={facecam_box['x']}, y={facecam_box['y']}, size={facecam_box['w']}x{facecam_box['h']}")
            print("       Layout selected: Split Screen (Top: Streamer, Bottom: Gameplay)")
        else:
            selected_layout = "blurred_bg"
            print("       No streamer facecam detected. Using: Blurred Background Layout")

    elif mode == "podcast":
        detector = PodcastLayoutDetector()
        speakers = detector.detect_podcast_speakers(video_file)
        if speakers and (layout_preference == "auto" or layout_preference == "split"):
            selected_layout = "podcast_split"
            layout_data = speakers
            print(f"       Podcast speakers detected! (Host & Guest)")
            print("       Layout selected: Dual-Speaker Split Screen (Top: Host, Bottom: Guest)")
        else:
            selected_layout = "blurred_bg"
            print("       Speakers not clearly separated. Using: Blurred Background Layout")

    elif mode == "talking_head":
        detector = TalkingHeadLayoutDetector()
        head_box = detector.detect_talking_head(video_file)
        if head_box and (layout_preference == "auto" or layout_preference == "portrait"):
            selected_layout = "talking_head"
            layout_data = head_box
            status = "Face tracked" if head_box.get("face_detected") else "Center framing"
            print(f"       Speaker framing ({status}): x={head_box['x']}, w={head_box['w']}, h={head_box['h']}")
            print("       Layout selected: 9:16 Portrait Auto-Reframe")
        else:
            selected_layout = "blurred_bg"
            print("       Using: Blurred Background Layout")

    # 4. Render Final Vertical Shorts (9:16) & Subtitles
    print(f"\n[4/4] 🎬 Processing Subtitles & Rendering 9:16 Shorts...")
    rendered_files = []
    sub_generator = SubtitleGenerator(model_name=whisper_model) if generate_subtitles else None

    for i, h in enumerate(highlights, 1):
        out_name = f"{mode}_clip_{i}.mp4"
        sub_ass = None
        transcript_text = ""

        if sub_generator:
            try:
                print(f"       🎙️ Transcribing Clip #{i} with Whisper AI ({whisper_model})...")
                clip_wav = os.path.join("downloads", f"audio_{i}.wav")
                extract_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(h["start"]),
                    "-t", str(clip_duration),
                    "-i", video_file,
                    "-vn", "-ac", "1", "-ar", "16000",
                    clip_wav
                ]
                subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ass_path = os.path.join("output", f"sub_{mode}_{i}.ass")
                sub_ass, transcript_text = sub_generator.generate_subtitles(clip_wav, ass_path)
                if os.path.exists(clip_wav):
                    try:
                        os.remove(clip_wav)
                    except Exception:
                        pass
            except Exception as e:
                print(f"       ⚠️ Subtitle warning: {e}. Rendering without subtitles...")
                sub_ass = None

        out_path = clipper.render_clip(
            input_video=video_file,
            start_sec=h["start"],
            duration=clip_duration,
            output_name=out_name,
            layout_mode=selected_layout,
            layout_data=layout_data,
            hook_title=hook_title,
            mode=mode,
            subtitle_ass_path=sub_ass
        )
        rendered_files.append(out_path)
        print(f"       ✅ Clip #{i} saved: {out_path}")

        # Social Pack
        social = copywriter.generate_social_pack(transcript_text, mode=mode, hook_title=hook_title)
        print(f"\n       📝 Social Media Copywriting (Clip #{i}):")
        print(f"       Title  : {social['title']}")
        print(f"       Caption:\n{social['caption']}\n")

    print("=" * 65)
    print(f"🎉 SUKSES! {len(rendered_files)} video shorts vertikal 9:16 siap diupload:")
    for f in rendered_files:
        print(f"   -> {os.path.abspath(f)}")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Multi-Mode Video Clipping App with Whisper Subtitles & CV Layouts")
    parser.add_argument("source", help="YouTube URL or local MP4 path")
    parser.add_argument("--mode", choices=["gaming", "podcast", "talking_head"], default="gaming", help="Content mode: gaming, podcast, talking_head")
    parser.add_argument("--start", type=int, default=120, help="Start time in seconds for analysis window (default: 120s)")
    parser.add_argument("--duration", type=int, default=180, help="Duration in seconds of window to analyze (default: 180s)")
    parser.add_argument("--clip-len", type=int, default=30, help="Length of each output short in seconds (default: 30s)")
    parser.add_argument("--top", type=int, default=1, help="Number of clips to generate (default: 1)")
    parser.add_argument("--layout", choices=["auto", "split", "portrait", "blur"], default="auto", help="Layout style")
    parser.add_argument("--hook", default=None, help="Hook title banner text")
    parser.add_argument("--no-subtitles", action="store_true", help="Disable Whisper auto-subtitles")
    parser.add_argument("--whisper-model", choices=["tiny", "base", "small"], default="base", help="Whisper model size")

    args = parser.parse_args()

    process_video(
        source=args.source,
        mode=args.mode,
        time_window_start=args.start,
        time_window_duration=args.duration,
        clip_duration=args.clip_len,
        top_k=args.top,
        layout_preference=args.layout,
        hook_title=args.hook,
        generate_subtitles=not args.no_subtitles,
        whisper_model=args.whisper_model
    )
