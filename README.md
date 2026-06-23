# LexiCast

Extract advanced English vocabulary and key phrases from any YouTube video — paste a link, get a curated word list grounded in real usage.

## How it works

1. You paste a YouTube URL
2. LexiCast tries to grab the auto-generated subtitles (fast)
3. If no subtitles exist, it downloads the audio and transcribes it locally with Whisper
4. The transcript is sent to Claude, which extracts 8–12 vocabulary words and 6–10 phrases
5. Results appear as expandable cards with definitions, context quotes, and usage tips

---

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- `ffmpeg` installed (required by Whisper for audio processing)
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg
  ```

### 1. Get an Anthropic API key

Sign up at [console.anthropic.com](https://console.anthropic.com), create a key, and set it:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add this to your `~/.zshrc` or `~/.bashrc` to make it permanent.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> **First run:** Whisper will automatically download the `base` model (~145MB) and cache it at `~/.cache/whisper/`. This happens only once.

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000)

---

## Whisper model sizes

If you want more accuracy (at the cost of speed), change `"base"` in `backend/main.py` to any of:

| Model    | Size   | Speed      | Accuracy  |
|----------|--------|------------|-----------|
| tiny     | ~39MB  | Very fast  | Lower     |
| base     | ~145MB | Fast       | Good      |
| small    | ~244MB | Moderate   | Better    |
| medium   | ~769MB | Slow       | Very good |
| large    | ~1.5GB | Very slow  | Best      |

For most podcasts and lectures, `base` or `small` is sufficient.

---

## Deployment

### Backend → Railway

1. Push the `backend/` folder to a GitHub repo
2. Create a new Railway project, connect the repo
3. Add environment variable: `ANTHROPIC_API_KEY=sk-ant-...`
4. Railway auto-detects Python and runs `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Frontend → Vercel

1. Update the fetch URL in `App.jsx` from `http://localhost:8000` to your Railway backend URL
2. Push `frontend/` to GitHub
3. Import into Vercel — it auto-detects Create React App

---

## Notes

- Videos must be public and in English
- Auto-generated subtitles are used when available (much faster than Whisper)
- Whisper transcription can take 30–90 seconds for longer videos
- The minimum transcript length is 30 words; very short clips will be rejected
