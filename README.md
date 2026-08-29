# Icon Captcha Solver Microservice

Dedicated, production-ready FastAPI microservice for solving LuckyWatch's custom 3-Icon Click Sequence Captchas using Multimodal Vision LLMs (`gemini/gemma-4-31b-it` and `gemini/gemini-3.7-flash` via 9router API).

---

## 🎯 Architecture & Specifications

1. **Multimodal Vision Strategy:**
   - **Input 1 (Queue Banner):** 88x24 px banner showing 3 target icons ordered strictly from left to right.
   - **Input 2 (Canvas):** 240x200 px image containing scattered neon outline icons.
   - **Prompt Pipeline:** Identifies the 3 target icons in exact sequence, then maps each icon to its center coordinates `(x, y)` on the canvas.
   - **Post-Processing:** Automatically clamps coordinates into `[0, 240]` for `x` and `[0, 200]` for `y`, applying even-pixel alignment (`x if x % 2 == 0 else x - 1`).

2. **9router Configuration:**
   - Base URL: `http://127.0.0.1:20128/v1` (Internal) / `https://9router.indrayuda.my.id/v1` (Public)
   - Primary Model: `gemini/gemma-4-31b-it`
   - Fallback Model: `gemini/gemini-3.7-flash`

3. **HTTP API Interface:**
   - Framework: FastAPI + Uvicorn
   - Port: `5073` (Configurable via `config.json`)
   - Daemon: Managed via `systemd` (`icon-captcha-solver.service`)

---

## 🚀 API Endpoints

### 1. Health Check
`GET /health`
```json
{
  "status": "healthy",
  "model": "gemini/gemma-4-31b-it",
  "fallback_model": "gemini/gemini-3.7-flash",
  "router_base_url": "http://127.0.0.1:20128/v1"
}
```

### 2. Solve Captcha (JSON)
`POST /solve`

**Request Body:**
```json
{
  "queue_base64": "data:image/png;base64,iVBORw0KGgoAAA...",
  "image_base64": "data:image/png;base64,iVBORw0KGgoAAA..."
}
```
*Note: Supports both raw Base64 strings and Data URLs.*

**Response:**
```json
{
  "status": "ok",
  "solution": [
    {"x": 164, "y": 164},
    {"x": 40, "y": 124},
    {"x": 210, "y": 40}
  ],
  "identified_icons": [
    "magician's hat",
    "stamp",
    "clapperboard"
  ],
  "latency_ms": 29519
}
```

### 3. Solve Captcha (Multipart Form / File Upload)
`POST /solve/form`

Accepts `queue_file` / `image_file` as file uploads or `queue_base64` / `image_base64` as form fields.

---

## 🛠️ Installation & Setup

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`

```bash
pip install -r requirements.txt
```

### Configuration (`config.json`)
```json
{
  "host": "0.0.0.0",
  "port": 5073,
  "router_base_url": "http://127.0.0.1:20128/v1",
  "router_public_base_url": "https://9router.indrayuda.my.id/v1",
  "router_api_key": "sk-...",
  "model": "gemini/gemma-4-31b-it",
  "fallback_model": "gemini/gemini-3.7-flash",
  "timeout_seconds": 180,
  "canvas_width": 240,
  "canvas_height": 200
}
```

### Run Locally
```bash
python3 main.py
```

### Run via systemd
```bash
sudo cp icon-captcha-solver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now icon-captcha-solver.service
```

---

## 🧪 Verification & Testing

Run unit & integration test suites:
```bash
pytest test_service.py -v
```

Execute live sample solver across real captcha datasets:
```bash
python3 test_live_execution.py
```
