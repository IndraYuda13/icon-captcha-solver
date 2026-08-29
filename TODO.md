# IconCaptchaSolver — Project Roadmap & Model Training TODO

## 🎯 Objective
Transition from relying on external cloud Vision LLM API calls (Gemini / 9router) to a **zero-token local lightweight neural network model** (YOLOv8-pose / Siamese ViT / CNN Landmark detector) that can solve LuckyWatch 3-Icon Sequence Captchas locally in <50ms with 0 API cost.

---

## 📋 Actionable Phases & Roadmap

### Phase 1: Automated Ground-Truth Dataset Harvester (Active Now)
- [x] Create dedicated dataset directory: `/root/projects/icon-captcha-solver/dataset/images/`
- [x] Auto-save raw queue banners (88x24 px) and canvas images (240x200 px) in lossless PNG format.
- [x] Store structured annotations in `dataset/annotations.jsonl`:
  ```json
  {
    "id": "sample_20260830_040512_a1b2",
    "timestamp": "2026-08-30T04:05:12Z",
    "queue_file": "images/sample_20260830_040512_a1b2_queue.png",
    "canvas_file": "images/sample_20260830_040512_a1b2_canvas.png",
    "solution": [{"x": 164, "y": 124}, {"x": 104, "y": 34}, {"x": 154, "y": 34}],
    "model": "ag/gemini-3.7-flash-high",
    "verified_by_server": true
  }
  ```
- [x] Add `/feedback` API endpoint so the claimer bot confirms when coordinates successfully unlock the real reward (+0.00025 USD), ensuring **100% verified ground truth only**.

---

### Phase 2: Dataset Curation & Augmentation
- [ ] Accumulate target volume: **500 - 1,000 verified sample pairs**.
- [ ] Catalog all unique pictogram icon classes (target ~50-80 unique icon archetypes).
- [ ] Data augmentation:
  - Random brightness / contrast shifts (simulating dark neon background variants).
  - Minor spatial jitter (±2 to 4 pixels).
  - Isolated icon cropping from 88x24 queue banners for template dictionary matching.

---

### Phase 3: Local Model Architecture & Training
- [ ] **Architecture Options:**
  - **Option A (Siamese Metric Learning / Template Matcher):** Crop 3 query icons -> compute embeddings via lightweight MobileNetV4 / EfficientNet -> match bounding contours on the 240x200 canvas.
  - **Option B (YOLOv8 / RT-DETR Keypoint Detector):** Train keypoint / bounding box detection on the canvas conditioned on class labels.
  - **Option C (Fine-tuned Tiny Vision LLM):** Fine-tune Qwen2.5-VL 3B or Moondream 2 / SmolVLM using LoRA for single-pass coordinate JSON outputs.
- [ ] Train locally on VPS GPU / CPU using PyTorch & ONNX Runtime.

---

### Phase 4: Production Deployment & Zero-Token Switch
- [ ] Convert trained model to **ONNX / TensorRT / OpenVINO** for sub-30ms inference.
- [ ] Add inference engine toggle in `config.json` (`"engine": "local_onnx"`).
- [ ] Keep Vision LLM as automatic fallback if local model confidence score is < 95%.
