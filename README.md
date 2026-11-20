# 🎮 AI Gaming Auto-Clipper (GTA VI & Gaming Edition) 9:16

Aplikasi otomatis untuk mengubah rekaman gameplay / livestream YouTube gaming panjang (hingga 24 jam) menjadi video vertikal **Shorts / TikTok / Reels (1080x1920)** dalam hitungan detik menggunakan AI Audio Spike Detection dan Computer Vision Facecam Tracking.

---

## ⚡ Fitur Utama

1. **Audio Spike & Decibel Peak Detection**:
   - Mendeteksi momen klimaks otomatis (reaksi kaget, tawa terbahak-bahak, teriakan streamer, ledakan/tembakan in-game).
   - Menghitung excitement score dan memotong klip 20–60 detik secara presisi.

2. **Computer Vision Streamer Facecam Tracking (OpenCV)**:
   - Mendeteksi posisi webcam streamer secara otomatis di sudut layar.
   - Mengubah video horizontal 16:9 menjadi **Split Screen Vertikal 9:16**:
     - **Atas**: Wajah streamer (reaksi)
     - **Bawah**: Layar gameplay utama
     - **Tengah**: Neon cyber divider line + Teks hook otomatis

3. **Cinematic Blurred Background Layout**:
   - Opsi untuk gameplay murni (tanpa streamer) dengan efek blur sinematik di latar atas dan bawah.

4. **Smart YouTube Slicer**:
   - Mampu memproses livestream marathon berdurasi puluhan jam tanpa harus mengunduh puluhan gigabyte secara penuh.

5. **Modern Cyberpunk Web UI**:
   - Dashboard web lokal berbasis FastAPI + HTML/JS untuk monitoring dan download MP4 satu klik.

---

## 🚀 Panduan Menjalankan di Rumah

### 1. Clone Repository
```bash
git clone git@github.com:yusufarifin100/ai-clipping-app.git
cd ai-clipping-app
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

> **Catatan FFmpeg**: Pastikan `ffmpeg` terpasang di komputer Anda. Jika belum ada di sistem PATH, Anda bisa menginstallnya lewat `winget install Gyan.FFmpeg` atau memanfaatkan package `imageio-ffmpeg`.

### 3. Jalankan Aplikasi

#### Cara 1: Buka Web Dashboard (Rekomendasi)
```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
```
Buka browser Anda di `http://127.0.0.1:8000`.

#### Cara 2: Lewat Command Line (CLI)
```bash
python main.py "https://www.youtube.com/watch?v=qSyo5d-dVzA" --start 300 --duration 180 --clip-len 30 --hook "GTA VI MOMENT 💀"
```

---

## 📁 Struktur Folder
```
ai-clipping-app/
├── core/
│   ├── analyzer/       # Deteksi lonjakan audio desibel
│   ├── downloader/     # YouTube smart slice downloader
│   ├── layout/         # Computer Vision Facecam detector
│   └── renderer/       # FFmpeg 9:16 vertical video renderer
├── web/
│   ├── app.py          # Backend FastAPI
│   └── index.html      # UI Dashboard
├── output/             # Folder hasil video shorts
├── downloads/          # Cache unduhan sementara
├── main.py             # CLI runner utama
└── requirements.txt
```
