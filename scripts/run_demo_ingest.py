from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import config_manager
from Stage_2.database import Database
from Stage_2.orchestrator import Orchestrator
from Stage_2.watcher import Watcher
from paths import ROOT_DIR
from plugin_discovery import discover_services, discover_tasks
from vectorai import get_vector_store


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-14s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("DemoIngest")


def _task_totals(task_stats: dict) -> tuple[int, int, int, int]:
    pending = processing = done = failed = 0
    for counts in task_stats.values():
        pending += int(counts.get("PENDING", 0))
        processing += int(counts.get("PROCESSING", 0))
        done += int(counts.get("DONE", 0))
        failed += int(counts.get("FAILED", 0))
    return pending, processing, done, failed


def _effective_pending(task_stats: dict, ignore_pending: set[str]) -> int:
    total = 0
    for task_name, counts in task_stats.items():
        if task_name in ignore_pending:
            continue
        total += int(counts.get("PENDING", 0))
    return total


def main():
    demo_dir = os.getenv("DEMO_DIR", "/app/demo_data")
    timeout_s = int(os.getenv("INGEST_TIMEOUT_S", "900"))
    poll_s = float(os.getenv("INGEST_POLL_S", "2"))
    ignore_pending = {
        t.strip()
        for t in os.getenv("IGNORE_PENDING_TASKS", "ocr_images").split(",")
        if t.strip()
    }

    logger.info("Starting demo ingestion run")
    logger.info("ROOT_DIR=%s", ROOT_DIR)
    logger.info("DEMO_DIR=%s", demo_dir)

    cfg = config_manager.load()
    cfg["sync_directories"] = [demo_dir]
    cfg["enabled_frontends"] = []
    cfg["autoload_services"] = []
    cfg["vectorai_enabled"] = True
    # In containerized compose, VectorAI is reachable by service name.
    cfg["vectorai_host"] = os.getenv("VECTORAI_HOST", "vectorai-db")
    cfg["vectorai_port"] = int(os.getenv("VECTORAI_PORT", "50051"))

    db = Database(cfg["db_path"])
    services = discover_services(ROOT_DIR, cfg)

    for svc_name in ("text_embedder", "image_embedder", "whisper"):
        svc = services.get(svc_name)
        if svc is None:
            raise RuntimeError(f"Required service not discovered: {svc_name}")
        if not svc.loaded:
            logger.info("Loading service: %s", svc_name)
            svc.load()

    orchestrator = Orchestrator(db, cfg, services)
    discover_tasks(ROOT_DIR, orchestrator, cfg)

    reset_tasks = [
        t.strip() for t in os.getenv("RESET_TASKS", "").split(",") if t.strip()
    ]
    for task_name in reset_tasks:
        logger.info("Resetting task to PENDING: %s", task_name)
        db.reset_task(task_name)

    watcher = Watcher(orchestrator, db, cfg)

    start = time.time()
    last_progress = start
    try:
        orchestrator.start()
        watcher.start()

        settled_cycles = 0
        while True:
            stats = db.get_system_stats()
            pending, processing, done, failed = _task_totals(stats.get("tasks", {}))
            effective_pending = _effective_pending(stats.get("tasks", {}), ignore_pending)
            with db.lock:
                files_total = int(db.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0])

            logger.info(
                "Progress files=%d pending=%d effective_pending=%d processing=%d done=%d failed=%d",
                files_total,
                pending,
                effective_pending,
                processing,
                done,
                failed,
            )

            if files_total > 0 and effective_pending == 0 and processing == 0:
                settled_cycles += 1
            else:
                settled_cycles = 0

            if settled_cycles >= 3:
                break

            if time.time() - start > timeout_s:
                raise TimeoutError(f"Ingestion did not settle within {timeout_s} seconds")

            if done > 0:
                last_progress = time.time()
            elif time.time() - last_progress > max(120, poll_s * 20):
                logger.warning("No task completions observed recently; still waiting")

            time.sleep(poll_s)

        vector_stats = get_vector_store(cfg).stats()
        final_stats = db.get_system_stats()
        with db.lock:
            files_total = int(db.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0])

        summary = {
            "ok": True,
            "demo_dir": demo_dir,
            "files_total": files_total,
            "files_by_modality": final_stats.get("files", {}),
            "tasks": final_stats.get("tasks", {}),
            "vectorai": vector_stats,
            "elapsed_s": round(time.time() - start, 2),
        }
        print(json.dumps(summary, indent=2))
    finally:
        try:
            watcher.stop()
        except Exception:
            pass
        try:
            orchestrator.stop()
        except Exception:
            pass
        for svc in services.values():
            if getattr(svc, "loaded", False):
                try:
                    svc.unload()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
