"""
IconCaptchaSolver Core Engine (High-Performance Vision Solver)
-------------------------------------------------------------
Solves visual 3-icon click sequence captchas in <4 seconds using 9router Vision LLMs.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("IconCaptchaSolver")


class CaptchaSolver:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        llm_cfg = self.config.get("llm", {})
        self.base_url = llm_cfg.get("base_url", "http://127.0.0.1:20128/v1").rstrip("/")
        self.api_key = llm_cfg.get("api_key", "")
        self.primary_model = llm_cfg.get("primary_model", "ag/gemini-3.7-flash-high")
        self.fallback_model = llm_cfg.get("fallback_model", "gemini/gemini-3.6-flash")
        self.timeout = llm_cfg.get("timeout_seconds", 15)
        self.max_tokens = llm_cfg.get("max_tokens", 500)

    def _clean_base64(self, raw: str) -> str:
        """Strip data:image/...;base64, prefixes and whitespace."""
        if "," in raw:
            raw = raw.split(",", 1)[1]
        return raw.strip()

    def _call_model(self, model: str, q_b64: str, img_b64: str) -> Tuple[str, int]:
        t0 = time.time()
        prompt_text = (
            "Task: Identify 3 target icons in Image 1 in exact sequence from left to right.\n"
            "Then in Image 2 (240x200 pixel canvas, (0,0) top-left), find the center (x, y) coordinates for each of the 3 target icons in exact order.\n\n"
            "Return ONLY a JSON array of coordinates:\n"
            '[{"x": 165, "y": 125}, {"x": 105, "y": 35}, {"x": 155, "y": 35}]'
        )

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{q_b64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as res:
            raw_body = res.read().decode("utf-8", errors="ignore")

        content = ""
        try:
            d = json.loads(raw_body)
            content = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            pass

        if not content:
            chunks = []
            for line in raw_body.splitlines():
                if line.startswith("data: ") and line.strip() != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            chunks.append(delta["content"])
                    except Exception:
                        pass
            content = "".join(chunks)

        dur_ms = int((time.time() - t0) * 1000)
        return content, dur_ms

    def solve(self, queue_base64: str, image_base64: str) -> Dict[str, Any]:
        """Solve 3-icon sequence captcha with primary and fallback models."""
        q_b64 = self._clean_base64(queue_base64)
        img_b64 = self._clean_base64(image_base64)

        models_to_try = [self.primary_model, self.fallback_model]
        last_error = ""

        for model_name in models_to_try:
            try:
                logger.info(f"⚡ Solving captcha with {model_name} (timeout: {self.timeout}s)...")
                content, latency = self._call_model(model_name, q_b64, img_b64)
                coords = self._extract_coordinates(content)

                if len(coords) >= 3:
                    solution = []
                    for pt in coords[:3]:
                        cx = max(0, min(240, int(pt[0])))
                        cy = max(0, min(200, int(pt[1])))
                        cx = cx if cx % 2 == 0 else cx - 1
                        cy = cy if cy % 2 == 0 else cy - 1
                        solution.append({"x": cx, "y": cy})

                    logger.info(f"✅ Captcha solved by {model_name} in {latency}ms -> {solution}")
                    return {
                        "status": "ok",
                        "solution": solution,
                        "latency_ms": latency,
                        "model": model_name,
                        "raw_output": content.strip(),
                    }
                else:
                    logger.warning(f"Model {model_name} returned insufficient coordinates: {content}")
                    last_error = f"Insufficient coordinates from {model_name}"
            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
                last_error = str(e)

        return {
            "status": "error",
            "message": f"All vision models failed: {last_error}",
            "latency_ms": 0,
        }

    def _extract_coordinates(self, text: str) -> List[Tuple[int, int]]:
        """Extract (x,y) points from JSON or text."""
        coords: List[Tuple[int, int]] = []

        try:
            clean = text
            if "```" in clean:
                blocks = re.findall(r"```(?:json)?(.*?)```", clean, re.DOTALL)
                if blocks:
                    clean = blocks[0].strip()

            parsed = json.loads(clean)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        if "x" in item and "y" in item:
                            coords.append((int(item["x"]), int(item["y"])))
                        elif "point" in item and isinstance(item["point"], (list, tuple)):
                            coords.append((int(item["point"][0]), int(item["point"][1])))
            elif isinstance(parsed, dict):
                pts = parsed.get("coordinates") or parsed.get("solution") or parsed.get("points")
                if isinstance(pts, list):
                    for item in pts:
                        if isinstance(item, dict) and "x" in item and "y" in item:
                            coords.append((int(item["x"]), int(item["y"])))
        except Exception:
            pass

        if len(coords) >= 3:
            return coords

        matches = re.findall(r'["\']?x["\']?\s*:\s*([0-9]+)\s*,\s*["\']?y["\']?\s*:\s*([0-9]+)', text)
        if matches:
            return [(int(m[0]), int(m[1])) for m in matches]

        matches_pts = re.findall(r'\[\s*([0-9]+)\s*,\s*([0-9]+)\s*\]', text)
        if matches_pts:
            return [(int(m[0]), int(m[1])) for m in matches_pts]

        return coords
