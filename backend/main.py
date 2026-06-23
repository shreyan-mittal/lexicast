import os
import re
import json
import tempfile
import subprocess
from typing import Optional

import anthropic
import whisper
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are an expert English linguist. From the transcript, extract:
- 8-12 vocabulary words: prioritise sophisticated synonyms, domain-specific terms, strong verbs, nuanced adjectives. Skip basic words. For each: word, part_of_speech, definition, example_from_audio (verbatim or near-verbatim quote from transcript), why_useful, difficulty (intermediate/advanced/sophisticated).
- 6-10 phrases: prioritise idioms, collocations, discourse markers, transition phrases. For each: phrase, meaning, example_from_audio, register (formal/informal/neutral/academic/professional), usage_tip.
- summary: 2-3 sentence overview of the audio content.

Return ONLY valid JSON with keys: vocabulary (array), phrases (array), summary (string). No markdown, no preamble. Always ground examples in the actual transcript."""


class URLRequest(BaseModel):
    url: str


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
YTDLP_PLAYER = []  # default client selection works best with cookies


def try_get_subtitles(url: str, tmpdir: str) -> Optional[str]:
    """Try auto-generated subtitles first, then manual."""
    for sub_type in ["--write-auto-sub", "--write-sub"]:
        result = subprocess.run(
            [
                "yt-dlp",
                sub_type,
                "--sub-lang", "en,en-IN,en-US,en-GB,en-AU",
                "--sub-format", "vtt",
                "--skip-download",
                "--no-playlist",
                *YTDLP_COOKIES,
                *YTDLP_PLAYER,
                "-o", os.path.join(tmpdir, "subtitle"),
                url,
            ],
            capture_output=True, text=True, timeout=120
        )
        print("subtitle stderr:", result.stderr[-500:] if result.stderr else "")
        # Find any .vtt file written
        for fname in os.listdir(tmpdir):
            if fname.endswith(".vtt"):
                fpath = os.path.join(tmpdir, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                cleaned = strip_subtitle_formatting(raw)
                if len(cleaned.split()) >= 30:
                    return cleaned
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
            *YTDLP_PLAYER,
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
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set in environment.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Transcript:\n\n{transcript}"}],
    )

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
        transcript = try_get_subtitles(url, tmpdir)
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
