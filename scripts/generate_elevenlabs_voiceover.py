from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ElevenLabs voiceover from text file")
    parser.add_argument("--text-file", default="DEMO_TELEPROMPTER.txt")
    parser.add_argument("--output", default="recordings/demo_voiceover.mp3")
    parser.add_argument("--voice-id", default="JBFqnCBsd6RMkjVDRZzb")
    parser.add_argument("--model-id", default="eleven_multilingual_v2")
    parser.add_argument("--stability", type=float, default=0.38)
    parser.add_argument("--similarity", type=float, default=0.78)
    parser.add_argument("--style", type=float, default=0.18)
    parser.add_argument("--speaker-boost", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not set")

    text_path = Path(args.text_file).resolve()
    if not text_path.exists():
        raise SystemExit(f"Text file not found: {text_path}")
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("Input text is empty")

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{args.voice_id}?output_format=mp3_44100_128"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": args.model_id,
        "voice_settings": {
            "stability": args.stability,
            "similarity_boost": args.similarity,
            "style": args.style,
            "use_speaker_boost": bool(args.speaker_boost),
        },
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    if resp.status_code >= 400:
        raise SystemExit(f"ElevenLabs error {resp.status_code}: {resp.text[:500]}")

    out_path.write_bytes(resp.content)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
