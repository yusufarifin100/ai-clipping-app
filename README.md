# 🎬 AI Multi-Mode Auto-Clipper 9:16 (Gaming • Podcast • Talking Head)

> **The Ultimate All-in-One AI Video Clipper**: Menggabungkan kecepatan scanning Audio Spike, deteksi Computer Vision Facecam untuk Gaming, framing Podcast/Talking Head, **Whisper Animated Subtitles** dinamis, dan **AI Social Copywriting**.

---

## ⚡ 3 Mode Konten & Keunggulan

### 1. 🎮 Mode Gaming & Streamer
- **Audio Spike Detection**: Mendeteksi momen klimaks instan (teriakan jumpscare, tawa histeris, clutch 1v5, ledakan gameplay).
- **CV Streamer Facecam Tracking**: Otomatis mendeteksi kotak webcam streamer di sudut layar horizontal 16:9 -> di-render menjadi **Split Screen Vertikal 9:16** (Atas: Webcam Streamer 1080x720, Bawah: Gameplay 1080x1200) dengan pembatas neon cyan/pink.
- **Smart YouTube Slicer**: Sanggup memotong video livestream marathon 10–24 jam langsung tanpa harus mengunduh puluhan gigabyte secara penuh.

### 2. 🎙️ Mode Podcast & Interview
- **Conversational Energy**: Mendeteksi pertukaran dialog intens dan tawa bersama antar-pembicara.
- **CV Dual-Speaker Split**: Mendeteksi 2 pembicara (Host di kiri & Guest di kanan) -> di-render menjadi **Dual-Speaker Split 9:16** (Atas: 1080x960 Host, Bawah: 1080x960 Guest) dengan divider emas/amber elegan.

### 3. 🗣️ Mode Talking Head & Commentary
- **Vocal Cadence**: Mengidentifikasi kejelasan vokal dan ritme bicara yang persuasif/menarik.
- **9:16 Portrait Auto-Reframe**: Melacak koordinat horizontal wajah kreator dan memusatkan crop vertikal tepat di badan/wajah kreator (1080x1920) untuk video edukasi, review, monolog, atau tips.

---

## ✨ Fitur Baru: Whisper Subtitles & Social Copywriting Pack

1. **✨ Animated Burnt-in Subtitles (Whisper AI)**:
   - Mentranskripsi audio secara lokal menggunakan model Whisper (`tiny`, `base`, `small`).
   - Membakar subtitle bergaya viral (Alex Hormozi style) dengan pergantian warna kuning/putih bergaris tepi tebal di tengah video.
2. **📋 AI Social Copywriting & Hashtags Generator**:
   - Otomatis menghasilkan judul viral, teks caption persuasif, dan kumpulan hashtag relevan (`#fyp #shorts #gaming #podcast`) siap post satu klik.

---

## 🚀 Panduan Menjalankan

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
> Pastikan `ffmpeg` sudah terpasang di sistem PATH Anda (misal via `winget install Gyan.FFmpeg`).

### 2. Jalankan Web Dashboard (Rekomendasi)
```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Buka browser di **`http://127.0.0.1:8000`**:
1. Pilih Mode (**Gaming**, **Podcast**, atau **Talking Head**).
2. Masukkan link YouTube atau path MP4 lokal.
3. Centang opsi **Bakar Subtitle Animasi (Whisper AI)** dan **Buat Judul & Caption Medsos Otomatis**.
4. Tekan **⚡ GENERATE CLIPS SEKARANG**.
5. Tonton video hasil render dan klik **📋 Copy Caption** untuk langsung diposting ke TikTok / Reels / Shorts!

### 3. Jalankan Lewat Command Line (CLI)

```bash
# Mode Gaming dengan Auto-Subtitle Whisper
python main.py "URL_YOUTUBE" --mode gaming --start 120 --duration 180 --clip-len 30

# Mode Podcast
python main.py "URL_YOUTUBE" --mode podcast --start 300 --duration 180 --clip-len 45

# Mode Talking Head tanpa subtitle
python main.py "URL_YOUTUBE" --mode talking_head --start 60 --duration 120 --clip-len 30 --no-subtitles
```

---

## 📁 Struktur File
```
ai-clipping-app/
├── core/
│   ├── analyzer/
│   │   └── audio_spike.py          # Analisis gelombang audio adaptif per mode
│   ├── downloader/
│   │   └── yt.py                   # YouTube smart slicer (yt-dlp)
│   ├── layout/
│   │   ├── gaming_layout.py        # OpenCV facecam streamer detector
│   │   ├── podcast_layout.py       # OpenCV dual-speaker (Host & Guest) detector
│   │   └── talking_head_layout.py  # OpenCV solo creator auto-reframe 9:16
│   ├── subtitles/
│   │   └── sub_generator.py        # Whisper AI dynamic animated ASS subtitle generator
│   ├── ai/
│   │   └── copywriter.py           # Social caption & viral title generator
│   └── renderer/
│       └── clipper.py              # FFmpeg 9:16 multi-layout & subtitle burning renderer
├── web/
│   ├── app.py                      # FastAPI multi-mode backend
│   └── index.html                  # Cyberpunk dashboard UI (Mode Selector, Subtitles & Copywriting)
├── output/                         # Hasil video shorts MP4
├── downloads/                      # Cache video sementara
├── main.py                         # CLI runner multi-mode
└── requirements.txt
```
