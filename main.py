#!/usr/bin/env python3
"""
IconCaptchaSolver Microservice Server (Pure Python Standard Library HTTP Server)
---------------------------------------------------------------------------------
Zero external dependencies (uses standard library http.server).
Features:
  - Gemma 4 31B & Gemini Flash Multimodal Vision solver.
  - Automated Ground-Truth Dataset Harvester & /feedback endpoint for ML training.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from harvester import DatasetHarvester
from solver import CaptchaSolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("IconCaptchaAPI")

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "server": {"host": "0.0.0.0", "port": 5073},
        "llm": {
            "base_url": "http://127.0.0.1:20128/v1",
            "api_key": "",
            "primary_model": "ag/gemini-3.7-flash-high",
            "fallback_model": "gemini/gemini-3.6-flash",
            "timeout_seconds": 15,
            "max_tokens": 500,
        },
        "dataset_collection": True,
    }


config = load_config()
solver = CaptchaSolver(config)
harvester = DatasetHarvester()


class Handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            data = {
                "status": "healthy",
                "service": "IconCaptchaSolver",
                "primary_model": solver.primary_model,
                "fallback_model": solver.fallback_model,
                "base_url": solver.base_url,
                "dataset_collection": config.get("dataset_collection", True),
                "port": config.get("server", {}).get("port", 5073),
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_POST(self):
        if self.path == "/solve" or self.path.startswith("/solve?"):
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Empty request body"}')
                return

            body = self.rfile.read(content_len).decode("utf-8", errors="ignore")
            try:
                payload = json.loads(body)
                q_b64 = payload.get("queue_base64")
                img_b64 = payload.get("image_base64")

                if not q_b64 or not img_b64:
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'{"status": "error", "message": "Both queue_base64 and image_base64 are required"}')
                    return

                res = solver.solve(queue_base64=q_b64, image_base64=img_b64)

                # Record dataset sample for future training
                if res.get("status") == "ok" and config.get("dataset_collection", True):
                    sample_id = harvester.record_sample(
                        queue_b64=q_b64,
                        image_b64=img_b64,
                        solution=res.get("solution", []),
                        model=res.get("model", ""),
                        latency_ms=res.get("latency_ms", 0),
                        verified=False,
                    )
                    res["sample_id"] = sample_id

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                logger.error(f"Solve error: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

        elif self.path == "/feedback" or self.path.startswith("/feedback?"):
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8", errors="ignore")
            try:
                payload = json.loads(body)
                sample_id = payload.get("sample_id")
                if sample_id and payload.get("verified", False):
                    harvester.mark_verified(sample_id)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(b'{"status": "ok", "message": "Feedback recorded"}')
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run():
    srv_cfg = config.get("server", {})
    host = srv_cfg.get("host", "0.0.0.0")
    port = int(srv_cfg.get("port", 5073))

    server = HTTPServer((host, port), Handler)
    logger.info(f"IconCaptchaSolver running on http://{host}:{port} (Dataset Harvesting: ACTIVE) ...")
    server.serve_forever()


if __name__ == "__main__":
    run()
