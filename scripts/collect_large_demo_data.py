from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


TEXT_EXT = {
    ".txt",
    ".md",
    ".rst",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".html",
    ".css",
}

DOC_EXT = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}

IMAGE_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
}

AUDIO_EXT = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".aac",
    ".ogg",
    ".wma",
}

SKIP_DIR_NAMES = {
    "appdata",
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    "tmp",
    "temp",
    "$recycle.bin",
}


@dataclass
class Limits:
    docs: int
    notes: int
    photos: int
    audio: int


def _category_for_extension(ext: str) -> str | None:
    if ext in DOC_EXT:
        return "docs"
    if ext in TEXT_EXT:
        return "notes"
    if ext in IMAGE_EXT:
        return "photos"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def _safe_user_roots() -> list[Path]:
    home = Path.home()
    roots = [
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Pictures",
        home / "Music",
        home / "Videos",
    ]
    return [p for p in roots if p.exists()]


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"sources": {}, "copied_at": []}
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {"sources": {}, "copied_at": []}


def _save_index(index_path: Path, payload: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parse_size_limit_mb(value: int) -> int:
    return max(1, value) * 1024 * 1024


def collect_large_demo_data(
    demo_dir: Path,
    roots: list[Path],
    limits: Limits,
    max_file_mb: int,
) -> dict:
    target_dirs = {
        "docs": demo_dir / "docs",
        "notes": demo_dir / "notes",
        "photos": demo_dir / "photos",
        "audio": demo_dir / "audio",
    }
    for d in target_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # Keep import bookkeeping outside searchable demo_data so it does not
    # pollute semantic/text retrieval results.
    index_path = demo_dir.parent / "scripts" / ".bulk_import_index.json"
    index = _load_index(index_path)
    seen_sources: dict[str, str] = dict(index.get("sources", {}))
    max_bytes = _parse_size_limit_mb(max_file_mb)

    counts = {
        "docs": 0,
        "notes": 0,
        "photos": 0,
        "audio": 0,
        "skipped_too_large": 0,
        "skipped_seen": 0,
        "errors": 0,
    }

    current_files = {
        "docs": sum(1 for _ in target_dirs["docs"].rglob("*") if _.is_file()),
        "notes": sum(1 for _ in target_dirs["notes"].rglob("*") if _.is_file()),
        "photos": sum(1 for _ in target_dirs["photos"].rglob("*") if _.is_file()),
        "audio": sum(1 for _ in target_dirs["audio"].rglob("*") if _.is_file()),
    }

    goal = {
        "docs": max(current_files["docs"], limits.docs),
        "notes": max(current_files["notes"], limits.notes),
        "photos": max(current_files["photos"], limits.photos),
        "audio": max(current_files["audio"], limits.audio),
    }

    def reached_goal() -> bool:
        return all(current_files[k] >= goal[k] for k in ("docs", "notes", "photos", "audio"))

    for root in roots:
        if reached_goal():
            break

        for dirpath, dirnames, filenames in os.walk(root):
            # prune heavy and irrelevant directories in-place
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIR_NAMES]
            pdir = Path(dirpath)
            if "appdata" in {part.lower() for part in pdir.parts}:
                continue

            for filename in filenames:
                if reached_goal():
                    break

                src = pdir / filename
                try:
                    if not src.is_file():
                        continue
                except OSError:
                    continue

                ext = src.suffix.lower()
                category = _category_for_extension(ext)
                if category is None:
                    continue

                if current_files[category] >= goal[category]:
                    continue

                src_key = str(src.resolve())
                if src_key in seen_sources:
                    counts["skipped_seen"] += 1
                    continue

                try:
                    size = src.stat().st_size
                except OSError:
                    counts["errors"] += 1
                    continue

                if size > max_bytes:
                    counts["skipped_too_large"] += 1
                    continue

                dst_name = f"{category}_{uuid.uuid4().hex[:12]}{ext}"
                dst = target_dirs[category] / dst_name
                try:
                    shutil.copy2(src, dst)
                    seen_sources[src_key] = str(dst.relative_to(demo_dir))
                    current_files[category] += 1
                    counts[category] += 1
                except Exception:
                    counts["errors"] += 1

    index["sources"] = seen_sources
    copied_at = list(index.get("copied_at", []))
    copied_at.append(
        {
            "ts": int(time.time()),
            "counts_added": {
                "docs": counts["docs"],
                "notes": counts["notes"],
                "photos": counts["photos"],
                "audio": counts["audio"],
            },
            "roots": [str(r) for r in roots],
            "max_file_mb": max_file_mb,
        }
    )
    index["copied_at"] = copied_at[-20:]
    _save_index(index_path, index)

    return {
        "added": {
            "docs": counts["docs"],
            "notes": counts["notes"],
            "photos": counts["photos"],
            "audio": counts["audio"],
        },
        "total_now": current_files,
        "goal": goal,
        "skipped_too_large": counts["skipped_too_large"],
        "skipped_seen": counts["skipped_seen"],
        "errors": counts["errors"],
        "roots_used": [str(r) for r in roots],
        "index_path": str(index_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect large real local data from laptop folders into demo_data/*"
    )
    parser.add_argument(
        "--demo-dir",
        default="demo_data",
        help="Demo data folder root (default: demo_data)",
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        help="Optional source roots. If omitted, uses Desktop/Documents/Downloads/Pictures/Music/Videos.",
    )
    parser.add_argument("--docs", type=int, default=120, help="Target total docs files")
    parser.add_argument("--notes", type=int, default=300, help="Target total notes files")
    parser.add_argument("--photos", type=int, default=800, help="Target total photo files")
    parser.add_argument("--audio", type=int, default=40, help="Target total audio files")
    parser.add_argument(
        "--max-file-mb",
        type=int,
        default=50,
        help="Skip source files larger than this size in MB (default: 50)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    demo_dir = Path(args.demo_dir).resolve()
    roots = [Path(r).resolve() for r in args.roots] if args.roots else _safe_user_roots()

    if not roots:
        print(json.dumps({"ok": False, "error": "No valid source roots found"}, indent=2))
        return 1

    limits = Limits(
        docs=max(1, args.docs),
        notes=max(1, args.notes),
        photos=max(1, args.photos),
        audio=max(1, args.audio),
    )
    result = collect_large_demo_data(
        demo_dir=demo_dir,
        roots=roots,
        limits=limits,
        max_file_mb=max(1, args.max_file_mb),
    )
    payload = {"ok": True, **result}
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
