# Edge-AI Surveillance & Real-Time Desktop Alerting Pipeline

A fully local, no-cloud desktop application that watches a live webcam feed, runs
real-time object detection (YOLOv8n via ONNX Runtime, CPU), and fires an on-screen +
audible + logged alert within about a second of detecting a person or vehicle.

## Features

- Live video panel with bounding-box + confidence overlays (PySide6/Qt UI).
- On-screen FPS and per-frame latency (ms) overlay.
- On qualifying detection: red on-screen alert banner, an audible alarm (via
  `winsound`), a Windows desktop toast notification (via `plyer`), and a structured
  row written to a local SQLite database with a saved JPEG snapshot.
- Camera capture and inference run on a background `QThread`; alert I/O (snapshot,
  DB write, sound, toast) runs on a second background thread, so nothing blocks the
  video loop or freezes the UI.
- Per-class alert cooldown to avoid re-triggering every frame on a sustained
  detection (`alerts.cooldown_seconds` in `config.yaml`).

## Performance

The camera capture backend uses Windows Media Foundation (`cv2.CAP_MSMF`), which on
this hardware negotiates a real, honest ~30 FPS at 640x480 - the legacy DirectShow
backend (`cv2.CAP_DSHOW`) reported it had accepted a 60 FPS request but actually only
delivered ~16-20 FPS, and inconsistently. **30 FPS is this webcam's true hardware
ceiling** - no software change can exceed what the sensor itself can produce; a 60-70
FPS webcam would be required to go higher.

Inference is no longer the bottleneck: YOLOv8n at 640x640 with `intra_op_threads: 8`
runs at ~34 FPS standalone, comfortably above the camera's 30 FPS ceiling, so the
full-resolution model is used by default with no FPS cost. If you're on a slower CPU
and see inference becoming the bottleneck (overall FPS well below your camera's rated
speed), drop to a smaller model: `python scripts/export_model.py 320` and set
`model.input_size: 320` in `config.yaml`.

## Known limitation

**Drone detection is out of scope.** COCO/YOLOv8n (the pretrained model this project
uses) has no "drone" class, and no other class (airplane/kite/bird) is used as a
proxy. Only `{person, car, truck, bus, motorcycle}` are detected — trespassers and
vehicles. Adding drone detection would require training or sourcing a separate
custom-labeled model.

## Setup

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Export the pretrained detection model to ONNX (one-time; downloads `yolov8n.pt`
   via `ultralytics` and exports it to `models/yolov8n.onnx`):
   ```
   python scripts\export_model.py
   ```
4. Generate the alarm sound asset (one-time; synthesized locally, no internet
   needed):
   ```
   python scripts\generate_alarm_wav.py
   ```
5. `ultralytics`/`torch` are only needed for step 3 and are never imported by the
   app itself. Optionally remove them afterward to shrink the environment:
   ```
   pip uninstall ultralytics torch
   ```

## Running

```
python main.py
```

The app opens the default webcam (`camera.index: 0` in `config.yaml`), shows the
live feed with detections overlaid, and fires alerts as configured.

## Configuration (`config.yaml`)

| Section | Key | Meaning |
|---|---|---|
| `camera` | `source_type`, `index`, `rtsp_url`, `file_path` | Video source; only `webcam` is wired into the UI today, but `create_capture()` already supports `rtsp`/`file`. |
| `camera` | `capture_width`, `capture_height`, `target_fps` | Requested capture format; actual FPS is capped by what your webcam hardware can really deliver (see Performance below). |
| `model` | `path`, `input_size`, `confidence_threshold`, `iou_threshold`, `intra_op_threads` | ONNX model path/resolution, detection thresholds, and CPU threads per inference call. `input_size` must match the `imgsz` the ONNX was exported with (`scripts/export_model.py [imgsz]`, default 640). |
| `detection` | `classes_of_interest` | Which of the 5 allowed classes trigger alerts. |
| `alerts` | `cooldown_seconds`, `sound_file`, `toast_enabled`, `snapshot_dir` | Alert behavior. |
| `database` | `path` | SQLite database file location. |
| `ui` | `window_title`, `banner_display_seconds` | UI cosmetics. |

## Data produced at runtime

- `snapshots/` — JPEG frame captured at the moment of each alert.
- `data/alerts.db` — SQLite table `alerts(id, timestamp, object_class, confidence, snapshot_path)`.
- `app.log` — application log file.

Inspect recent alerts:
```
sqlite3 data\alerts.db "select * from alerts order by id desc limit 5;"
```

## Project structure

```
main.py                 Entry point
config.yaml              Runtime configuration
app/
  config.py               Config dataclasses + loader
  coco_classes.py          COCO class names + allowed-class/threat-category maps
  video_source.py          Video capture factory (webcam/rtsp/file)
  detector.py              YOLOv8 ONNX Runtime inference (preprocess/NMS/postprocess)
  video_worker.py          Background QThread: capture + inference + overlay drawing
  alert_worker.py          Background QThread: snapshot save, DB insert, sound, toast
  db.py                    SQLite schema + helpers
  main_window.py           PySide6 UI + thread wiring
  logging_setup.py         Logging configuration
scripts/
  export_model.py          One-time: exports yolov8n.onnx
  generate_alarm_wav.py    One-time: synthesizes assets/alarm.wav
```
