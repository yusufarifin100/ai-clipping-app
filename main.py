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
    time_window_duration: int = 1440, # default 24h scan
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
    sub_generator = SubtitleGenerator(model_name=whisper_model) if generate_subtitles else None

    is_youtube = source.startswith("http://") or source.startswith("https://")
    total_sec = 0
    start_sec = time_window_start
    dur_sec = time_window_duration * 60 if time_window_duration > 0 else 0

    if is_youtube:
        print(f"\n[1/4] 🌐 Checking YouTube URL: {source}")
        info = downloader.get_info(source)
        title = info.get("title", "Video")
        total_sec = int(info.get("duration", 0))
        print(f"       Title   : {title}")
        print(f"       Duration: {total_sec // 3600}h {(total_sec % 3600) // 60}m {total_sec % 60}s")

        if dur_sec <= 0 or (start_sec + dur_sec) > total_sec:
            dur_sec = max(60, total_sec - start_sec)

    rendered_files = []

    # STRATEGY A: Long livestream (> 20 min) Audio-First Scan
    if is_youtube and dur_sec > 1200:
        print(f"\n[1/4] ⚡ Activating Smart Audio-First Scan for Long Livestream ({dur_sec // 3600}h {(dur_sec % 3600) // 60}m)...")
        audio_file = downloader.download_audio_stream(
            url=source,
            start_sec=start_sec,
            end_sec=start_sec + dur_sec,
            output_filename=f"{mode}_stream_audio.m4a"
        )

        print(f"\n[2/4] 🔊 Scanning audio energy peaks across the full window...")
        highlights = analyzer.analyze_highlights(
            audio_file,
            clip_duration=clip_duration,
            top_k=top_k,
            mode=mode
        )
        print(f"       Found {len(highlights)} peak moment(s) across entire stream:")
        for idx, h in enumerate(highlights, 1):
            abs_time = start_sec + h["start"]
            print(f"       #{idx}: {int(abs_time // 3600):02d}h{int((abs_time % 3600) // 60):02d}m{int(abs_time % 60):02d}s (Score: {h['score']})")

        print(f"\n[3/4 & 4/4] 🎬 Downloading HD video per segment & rendering 9:16 Shorts...")
        for idx, h in enumerate(highlights, 1):
            abs_start = max(0, int(start_sec + h["start"]))
            abs_end = abs_start + clip_duration
            time_label = f"{int(abs_start // 3600):02d}h{int((abs_start % 3600) // 60):02d}m{int(abs_start % 60):02d}s"

            print(f"\n--- Processing Clip #{idx} (at {time_label}) ---")
            clip_video = downloader.download_segment(
                url=source,
                start_sec=abs_start,
                end_sec=abs_end,
                output_filename=f"cli_seg_{idx}.mp4"
            )

            # Layout Detection
            selected_layout, layout_data = detect_layout_cli(mode, clip_video, layout_preference)

            # Subtitles
            sub_ass, transcript_text = None, ""
            if sub_generator:
                try:
                    ass_path = os.path.join("output", f"sub_{mode}_{idx}.ass")
                    sub_ass, transcript_text = sub_generator.generate_subtitles(clip_video, ass_path)
                except Exception as e:
                    print(f"       ⚠️ Subtitle warning: {e}")

            out_name = f"{mode}_clip_{idx}.mp4"
            out_path = clipper.render_clip(
                input_video=clip_video,
                start_sec=0,
                duration=clip_duration,
                output_name=out_name,
                layout_mode=selected_layout,
                layout_data=layout_data,
                hook_title=f"{hook_title} ({time_label})",
                mode=mode,
                subtitle_ass_path=sub_ass
            )
            rendered_files.append(out_path)
            print(f"       ✅ Clip #{idx} saved: {out_path}")

            social = copywriter.generate_social_pack(transcript_text, mode=mode, hook_title=hook_title)
            print(f"       📝 Caption:\n{social['caption']}\n")

    # STRATEGY B: Moderate or Short Slice / Local File
    else:
        video_file = source
        if is_youtube:
            print("       Downloading test segment...")
            video_file = downloader.download_segment(
                url=source,
                start_sec=start_sec,
                end_sec=start_sec + dur_sec,
                output_filename=f"{mode}_sample.mp4"
            )

        print(f"\n[2/4] 🔊 Analyzing Audio Highlights...")
        highlights = analyzer.analyze_highlights(
            video_file,
            clip_duration=clip_duration,
            top_k=top_k,
            mode=mode
        )

        selected_layout, layout_data = detect_layout_cli(mode, video_file, layout_preference)

        for idx, h in enumerate(highlights, 1):
            out_name = f"{mode}_clip_{idx}.mp4"
            sub_ass, transcript_text = None, ""
            if sub_generator:
                try:
                    clip_wav = os.path.join("downloads", f"audio_{idx}.wav")
                    extract_cmd = ["ffmpeg", "-y", "-ss", str(h["start"]), "-t", str(clip_duration), "-i", video_file, "-vn", "-ac", "1", "-ar", "16000", clip_wav]
                    subprocess.run(extract_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    ass_path = os.path.join("output", f"sub_{mode}_{idx}.ass")
                    sub_ass, transcript_text = sub_generator.generate_subtitles(clip_wav, ass_path)
                    if os.path.exists(clip_wav):
                        try: os.remove(clip_wav)
                        except Exception: pass
                except Exception as e:
                    print(f"       ⚠️ Subtitle warning: {e}")

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
            print(f"       ✅ Clip #{idx} saved: {out_path}")

            social = copywriter.generate_social_pack(transcript_text, mode=mode, hook_title=hook_title)
            print(f"       📝 Caption:\n{social['caption']}\n")

    print("\n" + "=" * 65)
    print(f"🎉 SUKSES! {len(rendered_files)} video shorts vertikal 9:16 siap diupload:")
    for f in rendered_files:
        print(f"   -> {os.path.abspath(f)}")
    print("=" * 65)

def detect_layout_cli(mode, video_file, layout_preference):
    selected_layout = "blurred_bg"
    layout_data = None
    if layout_preference == "blur":
        return "blurred_bg", None

    if mode == "gaming":
        detector = GamingLayoutDetector()
        facecam_box = detector.detect_streamer_facecam(video_file)
        if facecam_box and (layout_preference in ["auto", "split"]):
            selected_layout = "facecam_split"
            layout_data = facecam_box
            print(f"       Streamer facecam detected at: x={facecam_box['x']}, y={facecam_box['y']}")
    elif mode == "podcast":
        detector = PodcastLayoutDetector()
        speakers = detector.detect_podcast_speakers(video_file)
        if speakers and (layout_preference in ["auto", "split"]):
            selected_layout = "podcast_split"
            layout_data = speakers
            print("       Podcast dual speakers detected!")
    elif mode == "talking_head":
        detector = TalkingHeadLayoutDetector()
        head_box = detector.detect_talking_head(video_file)
        if head_box and (layout_preference in ["auto", "portrait"]):
            selected_layout = "talking_head"
            layout_data = head_box
            print("       Speaker tracked: 9:16 Portrait Auto-Reframe")

    return selected_layout, layout_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Multi-Mode Video Clipping App (24h Livestream Ready)")
    parser.add_argument("source", help="YouTube URL or local MP4 path")
    parser.add_argument("--mode", choices=["gaming", "podcast", "talking_head"], default="gaming", help="Content mode")
    parser.add_argument("--start", type=int, default=0, help="Start time in seconds (default: 0)")
    parser.add_argument("--duration", type=int, default=1440, help="Duration in minutes of window to analyze (default: 1440 = 24h)")
    parser.add_argument("--clip-len", type=int, default=30, help="Length of each output short in seconds (default: 30s)")
    parser.add_argument("--top", type=int, default=2, help="Number of clips to generate (default: 2)")
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
