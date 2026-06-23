import os
import re
import json
import time
import tempfile
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH, override=True)

import anthropic
import whisper
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_api_key():
    load_dotenv(_ENV_PATH, override=True)
    return os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are an expert English linguist and educator. From the transcript, extract as much as the content supports:

1. vocabulary (array) — Scale quantity to transcript length. Aim for 20-35 words for long content (30+ min), 10-20 for medium, 8-12 for short. Cover ALL difficulty levels proportionally. For each:
   - word, part_of_speech, definition, example_from_audio (verbatim or near-verbatim quote), why_useful, difficulty (intermediate/advanced/sophisticated)
   - Prioritise: sophisticated synonyms, domain-specific jargon, strong verbs, nuanced adjectives, business/academic terms. Skip common everyday words.

2. phrases (array) — Scale to 12-20 for long content, 8-12 for medium, 6-8 for short. For each:
   - phrase, meaning, example_from_audio, register (formal/informal/neutral/academic/professional), usage_tip
   - Prioritise: idioms, collocations, discourse markers, rhetorical devices, industry-specific expressions.

3. key_learnings (array) — The most important insights, ideas, or lessons from the content. Scale to 8-12 for long content, 5-8 for medium, 3-5 for short. For each:
   - insight (1 sentence, the core idea)
   - detail (2-3 sentences expanding on it)
   - quote (a verbatim or near-verbatim line from the transcript that supports it)

4. summary — 3-4 sentence overview covering the main topic, key speakers/context, and the central message.

Return ONLY valid JSON with keys: vocabulary, phrases, key_learnings, summary. No markdown, no preamble. Always ground examples and quotes in the actual transcript."""


GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
TO_EMAIL = os.environ.get("TO_EMAIL")


class URLRequest(BaseModel):
    url: str


class EmailRequest(BaseModel):
    source: str
    summary: str
    vocabulary: list
    phrases: list
    key_learnings: list
    word_count: int


def strip_subtitle_formatting(text: str) -> str:
    # Remove VTT/SRT timestamps
    text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}", "", text)
    # Remove sequence numbers on their own line
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove WEBVTT header and NOTE blocks
    text = re.sub(r"WEBVTT.*?\n", "", text)
    text = re.sub(r"NOTE\s.*?\n", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove VTT positioning cues
    text = re.sub(r"align:\w+\s+position:\S+\s+line:\S+\s+size:\S+", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def get_video_title(url: str) -> str:
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--no-playlist", url],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip() or "YouTube video"
    except Exception:
        return "YouTube video"


_COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")
YTDLP_COOKIES = ["--cookies", _COOKIES_FILE] if os.path.exists(_COOKIES_FILE) else []


def extract_video_id(url: str) -> Optional[str]:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def try_get_transcript(url: str) -> Optional[str]:
    """Fetch transcript via youtube-transcript-api (fast, no cookies needed)."""
    video_id = extract_video_id(url)
    if not video_id:
        return None
    try:
        api = YouTubeTranscriptApi()
        snippets = api.fetch(video_id, languages=["en", "en-IN", "en-US", "en-GB", "en-AU"])
        text = " ".join(s.text for s in snippets)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text.split()) >= 30 else None
    except Exception:
        return None


def transcribe_audio(url: str, tmpdir: str) -> str:
    audio_path = os.path.join(tmpdir, "audio.%(ext)s")
    result = subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "--no-playlist",
            *YTDLP_COOKIES,
            "-o", audio_path,
            url,
        ],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        err = result.stderr.strip().splitlines()
        last_err = err[-1] if err else "Unknown error"
        raise HTTPException(status_code=400, detail=f"yt-dlp failed: {last_err}")
    mp3_path = os.path.join(tmpdir, "audio.mp3")
    if not os.path.exists(mp3_path):
        # yt-dlp may keep original extension
        for fname in os.listdir(tmpdir):
            if fname.startswith("audio."):
                mp3_path = os.path.join(tmpdir, fname)
                break

    model = whisper.load_model("base")
    result = model.transcribe(mp3_path, fp16=False, language="en")
    return result["text"].strip()


def call_claude(transcript: str) -> dict:
    api_key = get_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set in .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    # For very long transcripts, sample intelligently to stay within context
    words = transcript.split()
    if len(words) > 18000:
        # Take beginning, middle, and end to cover the full content
        chunk = 6000
        sampled = (
            words[:chunk]
            + ["[... middle section ...]"]
            + words[len(words)//2 - chunk//2 : len(words)//2 + chunk//2]
            + ["[... later section ...]"]
            + words[-chunk:]
        )
        transcript_input = " ".join(sampled)
    else:
        transcript_input = transcript

    for attempt in range(4):
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Transcript:\n\n{transcript_input}"}],
            )
            break
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < 3:
                time.sleep(8 * (attempt + 1))
                continue
            raise

    raw = message.content[0].text.strip()

    # Strip markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract first {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise HTTPException(status_code=500, detail="Claude returned unparseable JSON.")


@app.post("/process")
async def process_url(body: URLRequest):
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided.")

    # Basic YouTube URL check
    if not re.search(r"(youtube\.com|youtu\.be)", url):
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube URL.")

    source = get_video_title(url)

    with tempfile.TemporaryDirectory() as tmpdir:
        transcript = try_get_transcript(url)
        method = "subtitles"

        if transcript is None:
            try:
                transcript = transcribe_audio(url, tmpdir)
                method = "whisper"
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Could not process audio: {str(e)}")

        word_count = len(transcript.split())
        if word_count < 30:
            raise HTTPException(status_code=400, detail=f"Transcript too short ({word_count} words). Need at least 30 words.")

        data = call_claude(transcript)

    return {
        **data,
        "source": source,
        "word_count": word_count,
        "transcript_preview": transcript[:500],
        "method": method,
    }


def build_email_html(data: EmailRequest) -> str:
    difficulty_colors = {
        "intermediate": "#0D9488", "advanced": "#2563EB", "sophisticated": "#7C3AED"
    }
    register_colors = {
        "formal": "#D97706", "informal": "#DB2777", "neutral": "#4B5563",
        "academic": "#1D4ED8", "professional": "#065F46"
    }

    learnings_html = "".join(f"""
        <div style="margin-bottom:16px;padding:16px;background:#FFFBEB;border-left:4px solid #F59E0B;border-radius:0 8px 8px 0;">
            <div style="font-weight:600;color:#111827;margin-bottom:6px">{i+1}. {l.get('insight','')}</div>
            <div style="color:#4B5563;font-size:14px;line-height:1.6">{l.get('detail','')}</div>
            {f'<div style="margin-top:10px;font-style:italic;color:#92400E;font-size:13px">"{l.get("quote","")}"</div>' if l.get('quote') else ''}
        </div>""" for i, l in enumerate(data.key_learnings))

    vocab_html = "".join(f"""
        <div style="margin-bottom:10px;padding:14px 16px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-family:Georgia,serif;font-size:16px;font-weight:700;color:#111827">{v.get('word','')}</span>
                <span style="font-size:12px;color:#9CA3AF;font-style:italic">{v.get('part_of_speech','')}</span>
                <span style="background:#EDE9FE;color:{difficulty_colors.get(v.get('difficulty','').lower(),'#374151')};font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px">{v.get('difficulty','').title()}</span>
            </div>
            <div style="margin-top:6px;color:#374151;font-size:14px">{v.get('definition','')}</div>
            {f'<div style="margin-top:6px;font-style:italic;color:#6B7280;font-size:13px;border-left:3px solid #3B82F6;padding-left:10px">"{v.get("example_from_audio","")}"</div>' if v.get('example_from_audio') else ''}
            {f'<div style="margin-top:4px;font-size:13px;color:#4B5563">💡 {v.get("why_useful","")}</div>' if v.get('why_useful') else ''}
        </div>""" for v in data.vocabulary)

    phrases_html = "".join(f"""
        <div style="margin-bottom:10px;padding:14px 16px;background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-family:Georgia,serif;font-size:15px;font-weight:700;color:#111827">"{p.get('phrase','')}"</span>
                <span style="background:#F3F4F6;color:{register_colors.get(p.get('register','').lower(),'#374151')};font-size:11px;font-weight:600;padding:2px 9px;border-radius:20px">{p.get('register','').title()}</span>
            </div>
            <div style="margin-top:6px;color:#374151;font-size:14px">{p.get('meaning','')}</div>
            {f'<div style="margin-top:6px;font-style:italic;color:#6B7280;font-size:13px;border-left:3px solid #10B981;padding-left:10px">"{p.get("example_from_audio","")}"</div>' if p.get('example_from_audio') else ''}
            {f'<div style="margin-top:4px;font-size:13px;color:#4B5563">✏️ {p.get("usage_tip","")}</div>' if p.get('usage_tip') else ''}
        </div>""" for p in data.phrases)

    return f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:680px;margin:0 auto;background:#F4F6FB;padding:24px;">
        <div style="background:#1A2035;border-radius:12px 12px 0 0;padding:20px 28px;">
            <span style="color:#fff;font-size:22px;font-weight:700">Lexi<span style="color:#60A5FA">Cast</span></span>
            <span style="color:#9CA3AF;font-size:13px;margin-left:12px">· {data.word_count:,} words processed</span>
        </div>

        <div style="background:#fff;padding:24px 28px;border:1px solid #E5E7EB;">
            <div style="font-size:12px;color:#6B7280;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px">📺 {data.source}</div>
            <div style="font-size:15px;color:#374151;line-height:1.7">{data.summary}</div>
            <div style="display:flex;gap:24px;margin-top:16px;padding-top:16px;border-top:1px solid #F3F4F6;">
                <div><span style="font-size:22px;font-weight:700;color:#60A5FA">{len(data.key_learnings)}</span><br><span style="font-size:11px;color:#9CA3AF;text-transform:uppercase">Key learnings</span></div>
                <div><span style="font-size:22px;font-weight:700;color:#60A5FA">{len(data.vocabulary)}</span><br><span style="font-size:11px;color:#9CA3AF;text-transform:uppercase">Vocab words</span></div>
                <div><span style="font-size:22px;font-weight:700;color:#60A5FA">{len(data.phrases)}</span><br><span style="font-size:11px;color:#9CA3AF;text-transform:uppercase">Phrases</span></div>
            </div>
        </div>

        <div style="background:#fff;padding:24px 28px;border:1px solid #E5E7EB;border-top:none;">
            <h2 style="font-size:16px;font-weight:700;color:#111827;margin:0 0 16px">🔑 Key Learnings</h2>
            {learnings_html}
        </div>

        <div style="background:#fff;padding:24px 28px;border:1px solid #E5E7EB;border-top:none;">
            <h2 style="font-size:16px;font-weight:700;color:#111827;margin:0 0 16px">📖 Vocabulary ({len(data.vocabulary)} words)</h2>
            {vocab_html}
        </div>

        <div style="background:#fff;padding:24px 28px;border:1px solid #E5E7EB;border-top:none;border-radius:0 0 12px 12px;">
            <h2 style="font-size:16px;font-weight:700;color:#111827;margin:0 0 16px">💬 Phrases ({len(data.phrases)} phrases)</h2>
            {phrases_html}
        </div>

        <div style="text-align:center;margin-top:16px;font-size:12px;color:#9CA3AF;">Sent by LexiCast</div>
    </div>"""


@app.post("/send-email")
async def send_email(data: EmailRequest):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not TO_EMAIL:
        raise HTTPException(status_code=500, detail="Email not configured. Set GMAIL_USER, GMAIL_APP_PASSWORD, and TO_EMAIL env vars.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"LexiCast: {data.source}"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(build_email_html(data), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"status": "sent"}
