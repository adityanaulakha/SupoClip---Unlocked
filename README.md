<p align="center">
  <a href="https://github.com/adityanaulakha/SupoClip---Unlocked">
    <img src="assets/banner.jpg" alt="SupoClip dashboard with video input, caption controls, and recent clips" width="100%" />
  </a>
</p>

<h1 align="center">SupoClip Unlocked 🎬</h1>

<p align="center">
  <strong>100% Free & Open-Source AI Video & Live Stream Clipping Platform</strong><br>
  Turn long videos & live streams into viral 9:16 vertical shorts with face tracking, animated captions, and virality scoring. No paywalls, no watermarks, no subscription limits.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="License: AGPL-3.0" /></a>
  <a href="docs/README.md"><img src="https://img.shields.io/badge/docs-docs%2F-green.svg" alt="Documentation" /></a>
  <img src="https://img.shields.io/badge/mode-100%25%20Free%20%2F%20Self--Hosted-brightgreen.svg" alt="Free & Unlocked" />
  <img src="https://img.shields.io/badge/live%20streams-supported-red.svg" alt="Live Streams Supported" />
</p>

---

## ⚡ What is SupoClip Unlocked?

SupoClip Unlocked is a fully featured, self-hostable AI video clipping platform. Give it any long video or **ongoing live stream** (YouTube, Twitch, Kick, or local file upload), and it automatically:
- 🔴 **Captures & Records Live Streams** directly from YouTube Live, Twitch, and Kick using configurable recording windows (5m, 10m, 15m, 30m, 45m, 60m).
- 🎙️ **Transcribes with Word-Level Precision** using AssemblyAI or local Whisper.
- 🧠 **Extracts Viral Moments** using Google Gemini (e.g. Gemini 3.1 Flash Lite), OpenAI, Claude, or local Ollama with zero reasoning stalls.
- 📊 **Scores Virality** with breakdown metrics (Hook, Engagement, Value, Shareability) and punchy AI hook headlines.
- 📱 **Reframes to 9:16 Vertical** with intelligent face detection to keep speakers centered.
- 💬 **Generates Animated Captions** with word-by-word highlight animations and customizable font presets.
- 🎞️ **Adds AI B-Roll** using free Pexels stock footage overlays.
- ✂️ **Built-in Studio Editor** to trim, split, re-caption, and export directly.
- 🔓 **Zero Billing Gates**: No Stripe required, no minute limits, no paywalls.

---

## 🚀 Quick Start (Local Setup)

Anyone can fork or clone this repository and have a full production-grade AI clipping suite running in under 5 minutes.

### 1. Prerequisites
- **Docker & Docker Compose** installed ([Get Docker](https://docs.docker.com/get-docker/))
  - *Recommended Docker Desktop resources*: At least 4 GB to 8 GB of RAM allocated for video rendering.
- **Git**

### 2. Required API Keys (Free Tier available for both)
1. **AssemblyAI API Key** (for fast word-level audio transcription):
   - Get a free key at [assemblyai.com](https://www.assemblyai.com/)
2. **Google Gemini API Key** (for AI highlight detection & scoring):
   - Get a free API key at [Google AI Studio (aistudio.google.com)](https://aistudio.google.com/)
   - *Recommended model*: `google-gla:gemini-3.1-flash-lite` (extremely fast, zero latency hang, generous free tier limits).

*(Optional)* **Pexels API Key** (for AI B-roll cutaway footage):
- Free key from [pexels.com/api](https://www.pexels.com/api/)

---

### 3. Setup in 3 Simple Steps

#### Step 1: Clone the Repository
```bash
git clone https://github.com/adityanaulakha/SupoClip---Unlocked.git
cd SupoClip---Unlocked
```

#### Step 2: Configure Environment Variables
Copy the example environment template:
```bash
cp .env.example .env
```

Open `.env` and fill in your keys:
```env
# Required for transcription
ASSEMBLY_AI_API_KEY=your_assemblyai_api_key_here

# Required for AI highlight analysis (Gemini is recommended and cost-effective)
LLM=google-gla:gemini-3.1-flash-lite
GOOGLE_API_KEY=your_google_gemini_api_key_here

# (Optional) For AI B-roll stock video overlays
PEXELS_API_KEY=your_pexels_key_here
```

> **Note on Monetization**: Billing is disabled by default in self-hosted mode (`MONETIZATION_ENABLED=false`). You have unlimited processing minutes out of the box.

#### Step 3: Start the Docker Stack
```bash
docker-compose up -d --build
```

This starts:
- **Frontend** (`supoclip-frontend`): Next.js App Router on [http://localhost:3107](http://localhost:3107)
- **API Backend** (`supoclip-backend`): FastAPI on [http://localhost:8000](http://localhost:8000) (Interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs))
- **Worker** (`supoclip-worker`): Async video processing & ffmpeg render pipeline
- **Cron Worker** (`supoclip-cron`): Scheduled background tasks
- **Database** (`supoclip-postgres`): PostgreSQL 15
- **Queue/Cache** (`supoclip-redis`): Redis 7

---

## 🎥 Using Live Stream Clipping

1. Open [http://localhost:3107](http://localhost:3107) in your browser.
2. Sign up with an email and password (local authentication; no email verification required).
3. In the input box on the dashboard, paste any live stream URL:
   - **YouTube Live**: `https://www.youtube.com/live/VIDEO_ID` or standard `watch?v=` links
   - **Twitch Channel**: `https://twitch.tv/streamer_name`
   - **Kick Channel**: `https://kick.com/streamer_name`
4. The **Live Stream** badge will activate automatically.
5. Select your desired recording duration (e.g. 5 min, 10 min, 15 min, 30 min, 45 min, or 60 min).
6. Click **Generate Clips**.
7. SupoClip will capture the live window, extract high-engagement highlights, generate subtitles and virality scores, and render ready-to-post 9:16 vertical clips!

---

## 🛠️ Architecture & Stack

| Component | Technology | Description |
|---|---|---|
| **Frontend** | Next.js 15, React 19, TailwindCSS, Radix UI | Dashboard, Studio video editor, real-time pipeline progress |
| **Backend API** | Python 3.11, FastAPI, Pydantic | REST API, authentication middleware, task coordination |
| **Video Processing Worker** | ARQ, ffmpeg, yt-dlp, OpenCV | Media remuxing, face tracking, 9:16 reframing, caption burning |
| **AI Highlight Engine** | Google Gemini (`gemini-3.1-flash-lite`), OpenAI, Anthropic, Ollama | Zero-latency transcript analysis and virality calibration |
| **Database & Cache** | PostgreSQL 15, Redis 7 | State persistence, task queues, idempotent jobs |

---

## 🔍 Helpful Commands

### View Service Logs
Stream live worker logs to see stream downloads, transcription, and clip rendering:
```bash
# View video processing worker logs
docker logs -f supoclip-worker

# View all container logs
docker-compose logs -f
```

### Stop / Restart Stack
```bash
# Stop all services
docker-compose down

# Restart worker after environment changes
docker restart supoclip-worker supoclip-backend
```

### Running Automated Tests
```bash
# Run backend test suite (unit tests for live stream, sources, and preflight)
docker exec supoclip-backend /app/.venv/bin/pytest tests/unit/test_live_stream.py tests/unit/test_stream_source.py --no-cov

# Run frontend tests
docker exec supoclip-frontend pnpm exec vitest run src/lib/video-upload.test.ts src/components/home-app.test.tsx
```

---

## 💡 Troubleshooting & FAQ

- **Port Conflict**: If port `3107` or `8000` is already in use, modify `FRONTEND_PORT` or `PORT` in your `.env` file.
- **Apple Silicon (M1/M2/M3/M4 Macs)**: Docker emulates `linux/amd64` by default with CPU-only acceleration, working out of the box. Ensure Docker Desktop has Rosetta enabled in settings for fastest performance.
- **Docker Disk Space**: Processing many high-definition video files can consume disk storage over time. You can clear temporary files anytime from the `uploads/` folder or prune Docker cache with `docker system prune`.
- **Using Ollama / 100% Local**: To run completely local with no cloud API keys, set `TRANSCRIPTION_PROVIDER=whisper` and `LLM=ollama:YOUR_MODEL`. See [`docs/configuration.md`](docs/configuration.md) for details.

---

## 📄 License

SupoClip is released under the [AGPL-3.0 License](LICENSE). Contributions, forks, and pull requests are welcome!
