"""
Transcribe Audio task.

Uses the local Whisper service to convert audio files into text and writes
the transcript into extracted_text so the existing text pipeline can chunk,
embed, and index it for search.
"""

import logging
import time
from pathlib import Path

from Stage_2.BaseTask import BaseTask, TaskResult

logger = logging.getLogger("TranscribeAudio")


class TranscribeAudio(BaseTask):
	name = "transcribe_audio"
	modalities = ["audio"]
	reads = []
	writes = ["extracted_text"]
	requires_services = ["whisper"]
	output_schema = """
		CREATE TABLE IF NOT EXISTS extracted_text (
			path TEXT PRIMARY KEY,
			content TEXT,
			char_count INTEGER,
			also_contains TEXT,
			extracted_at REAL
		);
	"""
	batch_size = 1
	max_workers = 1
	timeout = 1800

	def run(self, paths, context):
		whisper = context.services.get("whisper")
		if whisper is None or not whisper.loaded:
			return [TaskResult.failed("whisper service not loaded") for _ in paths]

		results = []
		for path in paths:
			try:
				transcript = whisper.transcribe(path) or ""
				transcript = transcript.strip()
				if not transcript:
					results.append(TaskResult.failed("No transcript generated"))
					continue

				logger.info(
					f"Transcribed {Path(path).name}: {len(transcript)} chars"
				)
				results.append(
					TaskResult(
						success=True,
						data=[{
							"path": path,
							"content": transcript,
							"char_count": len(transcript),
							"also_contains": "",
							"extracted_at": time.time(),
						}],
					)
				)
			except Exception as e:
				results.append(TaskResult.failed(str(e)))
		return results
