from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests


def _pick_image(image_path: str | None) -> Path | None:
    if image_path:
        p = Path(image_path).expanduser().resolve()
        return p if p.exists() else None

    photos_dir = Path("demo_data/photos").resolve()
    if not photos_dir.exists():
        return None

    for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"):
        match = next(photos_dir.glob(ext), None)
        if match:
            return match
    return None


def _expect(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke check FastAPI endpoints for demo readiness")
    parser.add_argument("--base", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--image", default=None, help="Optional image path for /api/search/image")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout seconds")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    timeout = args.timeout

    failures: list[str] = []
    summary: dict[str, object] = {"base": base}

    try:
        health = requests.get(f"{base}/health", timeout=timeout)
        health.raise_for_status()
        health_j = health.json()
        summary["health"] = health_j
        _expect(bool(health_j.get("ok")), "GET /health returned ok=false", failures)
    except Exception as exc:
        failures.append(f"GET /health failed: {exc}")

    try:
        status = requests.get(f"{base}/api/index/status", timeout=timeout)
        status.raise_for_status()
        status_j = status.json()
        summary["index_status"] = {
            "files_total": status_j.get("files_total"),
            "files_by_modality": status_j.get("files_by_modality"),
            "vectorai": status_j.get("vectorai"),
        }
        _expect(int(status_j.get("files_total") or 0) > 0, "files_total is 0", failures)
        _expect(
            bool((status_j.get("vectorai") or {}).get("available")),
            "VectorAI not available in /api/index/status",
            failures,
        )
    except Exception as exc:
        failures.append(f"GET /api/index/status failed: {exc}")

    try:
        search = requests.get(
            f"{base}/api/search",
            params={"q": "hackathon battle plan", "top_k": 5},
            timeout=timeout,
        )
        search.raise_for_status()
        search_j = search.json()
        summary["search"] = {
            "query": search_j.get("query"),
            "count": search_j.get("count"),
            "first_result": (search_j.get("results") or [{}])[0].get("meta", {}).get("path"),
        }
        _expect(int(search_j.get("count") or 0) > 0, "GET /api/search returned 0 results", failures)
    except Exception as exc:
        failures.append(f"GET /api/search failed: {exc}")

    img = _pick_image(args.image)
    if img is None:
        failures.append("No image file found for POST /api/search/image")
    else:
        try:
            with img.open("rb") as f:
                image_res = requests.post(
                    f"{base}/api/search/image",
                    params={"top_k": 5},
                    files={"file": (img.name, f)},
                    timeout=timeout,
                )
            image_res.raise_for_status()
            image_j = image_res.json()
            summary["image_search"] = {
                "upload": str(img),
                "count": image_j.get("count"),
                "first_result": (image_j.get("results") or [{}])[0].get("meta", {}).get("path"),
            }
            _expect(int(image_j.get("count") or 0) > 0, "POST /api/search/image returned 0 results", failures)
        except Exception as exc:
            failures.append(f"POST /api/search/image failed: {exc}")

    try:
        audio = requests.get(
            f"{base}/api/search",
            params={"q": "be decent in my eyes", "file_type": "mp3", "top_k": 5},
            timeout=timeout,
        )
        audio.raise_for_status()
        audio_j = audio.json()
        summary["audio_search"] = {
            "count": audio_j.get("count"),
            "first_result": (audio_j.get("results") or [{}])[0].get("meta", {}).get("path"),
        }
        _expect(
            int(audio_j.get("count") or 0) > 0,
            "GET /api/search audio query returned 0 results",
            failures,
        )
    except Exception as exc:
        failures.append(f"Audio query check failed: {exc}")

    print(json.dumps(summary, indent=2))
    if failures:
        print("\nFAILED CHECKS:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("\nAll endpoint checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
