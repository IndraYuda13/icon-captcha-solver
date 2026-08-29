"""
Dataset Harvester Module for IconCaptchaSolver
----------------------------------------------
Automatically records raw captcha images (queue & canvas) and their verified
ground-truth click coordinates into lossless PNGs and annotations.jsonl.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DatasetHarvester")

DATASET_DIR = Path(__file__).parent / "dataset"
IMAGES_DIR = DATASET_DIR / "images"
ANNOTATIONS_FILE = DATASET_DIR / "annotations.jsonl"


class DatasetHarvester:
    def __init__(self):
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def record_sample(
        self,
        queue_b64: str,
        image_b64: str,
        solution: List[Dict[str, int]],
        model: str,
        latency_ms: int,
        verified: bool = False,
    ) -> str:
        """Save image pair and record entry in annotations.jsonl."""
        sample_id = f"sample_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        q_filename = f"{sample_id}_queue.png"
        img_filename = f"{sample_id}_canvas.png"

        q_path = IMAGES_DIR / q_filename
        img_path = IMAGES_DIR / img_filename

        try:
            # Decode and save lossless PNGs
            if "," in queue_b64:
                queue_b64 = queue_b64.split(",", 1)[1]
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]

            q_path.write_bytes(base64.b64decode(queue_b64))
            img_path.write_bytes(base64.b64decode(image_b64))

            record = {
                "id": sample_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "queue_file": f"images/{q_filename}",
                "canvas_file": f"images/{img_filename}",
                "solution": solution,
                "model": model,
                "latency_ms": latency_ms,
                "verified_by_server": verified,
            }

            with open(ANNOTATIONS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            logger.info(f"📁 Dataset sample recorded: {sample_id} (Solution: {solution})")
            return sample_id
        except Exception as e:
            logger.error(f"Failed to record dataset sample: {e}")
            return ""

    def mark_verified(self, sample_id: str):
        """Update sample verification status when server awards reward."""
        if not ANNOTATIONS_FILE.exists() or not sample_id:
            return

        try:
            lines = ANNOTATIONS_FILE.read_text(encoding="utf-8").splitlines()
            updated_lines = []
            for line in lines:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("id") == sample_id:
                        data["verified_by_server"] = True
                    updated_lines.append(json.dumps(data))
                except Exception:
                    updated_lines.append(line)

            ANNOTATIONS_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            logger.info(f"⭐ Sample {sample_id} marked as 100% VERIFIED Ground Truth!")
        except Exception as e:
            logger.error(f"Error marking sample verified: {e}")
