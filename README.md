# LexiCast

Extract advanced English vocabulary, key phrases, and core insights from any YouTube video — paste a link, get a curated breakdown grounded in real usage, and optionally email it to yourself.

## How it works

1. Paste a YouTube URL
2. LexiCast fetches the transcript via the YouTube Transcript API (fast, no download needed)
3. If no transcript is available, it downloads the audio and transcribes it locally with Whisper
4. The transcript is sent to Claude, which extracts:
   - **Key learnings** — the most important insights with supporting quotes
   - **Vocabulary** — sophisticated words with definitions and in-context examples
   - **Phrases** — idioms, collocations, and discourse markers with usage tips
5. Results appear as expandable cards; hit **Send to email** to get a styled HTML digest in your inbox

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- `ffmpeg` (only needed for Whisper fallback)
  ```bash
  brew install ffmpeg          # macOS
  sudo apt install ffmpeg     # Ubuntu/Debian
  ```

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements-local.txt   # includes Whisper for local fallback
```

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Optional — required only for the Send to email feature
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password (not your login password)
TO_EMAIL=recipient@example.com
```

> To generate a Gmail App Password: Google Account → Security → 2-Step Verification → App passwords.

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000)

---

## Email digest

When `GMAIL_USER`, `GMAIL_APP_PASSWORD`, and `TO_EMAIL` are set in `backend/.env`, the **Send to email** button in the header delivers a fully formatted HTML email with all key learnings, vocabulary, and phrases — useful for reviewing on the go.

---

## Whisper fallback

If a YouTube transcript isn't available, LexiCast falls back to local Whisper transcription.

| Model  | Size   | Speed      | Accuracy  |
|--------|--------|------------|-----------|
| tiny   | ~39MB  | Very fast  | Lower     |
| base   | ~145MB | Fast       | Good      |
| small  | ~244MB | Moderate   | Better    |
| medium | ~769MB | Slow       | Very good |
| large  | ~1.5GB | Very slow  | Best      |

Change the model name in `backend/main.py` (`whisper.load_model(...)`) to trade speed for accuracy. `base` is the default and works well for most podcasts and lectures.

> First run: Whisper downloads the model (~145MB for `base`) to `~/.cache/whisper/` — one-time only.

---

## Deployment (free)

### Backend → Render

1. Go to [render.com](https://render.com), create a new **Web Service**, connect your GitHub repo
2. Set **Root Directory** to `backend`
3. Set **Build Command** to `pip install -r requirements.txt`
4. Set **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `TO_EMAIL`
6. Deploy — copy the public URL (e.g. `https://lexicast.onrender.com`)

> Render's free tier spins down after 15 min of inactivity — the first request may take ~30–60s to wake up. Whisper is not available in production; videos without a YouTube transcript will return a friendly error instead.

### Frontend → Vercel

1. In `frontend/src/App.jsx`, replace `http://localhost:8000` with your Render URL
2. Go to [vercel.com](https://vercel.com), import your repo, set **Root Directory** to `frontend`
3. Deploy

### Local vs production requirements

| File | Used for |
|---|---|
| `requirements-local.txt` | Local dev — includes Whisper + torch |
| `requirements.txt` | Production (Render) — lightweight, no Whisper |

---

## Notes

- Videos must be public and in English
- Transcripts are capped at ~18,000 words; longer videos are intelligently sampled (beginning, middle, end)
- Minimum transcript length is 30 words — very short clips are rejected
- The `.env` file is reloaded on each request, so key changes take effect without restarting the server
