# MRO Vision Control: Real-Time Structural Defect Inspection Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat&logo=react&logoColor=white)](https://react.dev/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX--Runtime-Accelerated-00599C.svg?style=flat&logo=microsoft&logoColor=white)](https://onnxruntime.ai/)
[![Docker](https://img.shields.io/badge/Docker-Orchestrated-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An edge-deployable, full-stack computer vision system designed for autonomous concrete defect detection (cracks, rebar, spalling, and unexposed bars). The project processes raw high-frequency camera streams and inspection drone footage, overlays computer vision bounding boxes dynamically, compiles real-time telemetry datasets, and exposes interactive analytics via a responsive Web UI.

---

## Repository Structure

```
├── backend/
│   ├── app.py                     # FastAPI ASGI Server & Inference Engine
│   ├── database.py                # SQLite Database CRUD & Persistence Layer
│   ├── requirements.txt           # Python Dependency Declarations
│   ├── best.pt                    # Custom YOLOv8 Model Weights (PyTorch)
│   ├── best.onnx                  # Optimized YOLOv8 ONNX Weights (Auto-Generated)
│   ├── get_openh264.py            # Cisco OpenH264 Binary Downloader
│   ├── Dockerfile                 # Backend Containerization Specification
│   ├── static/                    # Processed Video Streams & HLS Segments
│   │   └── videos/
│   └── temp_uploads/              # Temporary Upload Directory (Ignored in Git)
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # React App Dashboard with SVG Charts & Bounding Overlays
│   │   ├── App.css                # App CSS rules
│   │   ├── index.css              # Custom Vanilla HUD Styling System
│   │   └── main.jsx               # React entry point
│   ├── index.html                 # Entry HTML Document
│   ├── package.json               # Node Package configuration
│   ├── vite.config.js             # Vite compiler config
│   └── Dockerfile                 # Multi-stage Nginx Frontend Specification
├── docker-compose.yml             # Orchestration config for E2E deployment
├── migrate_videos.py              # Auxiliary utility for video codec migration
├── defect_detection_training.ipynb # Custom YOLOv8 Model Training Notebook
├── .gitignore                     # VCS exclusion patterns (Database, Node/Python libs, uploads)
└── README.md                      # Core Project Documentation
```

---

## Technical Architecture & Data Flow

```mermaid
graph TD
    %% Frontend Subsystem
    subgraph Client [Client UI - React 19 / Vite]
        A[HTML5 Webcam / Video Element]
        B[File Upload: Dropzone]
        C["Hls.js live player & Seekable player"]
        D[Canvas Overlay Bounding Boxes]
        E[Custom SVG Analytics Charts]
    end

    %% Backend Subsystem
    subgraph Server [FastAPI ASGI Server / Uvicorn]
        F[POST /api/process-frame]
        G[POST /api/upload-video]
        H["GET /api/tasks/{task_id}"]
        I["GET /api/videos/{task_id}"]
        J["GET /api/videos/{task_id}/download"]
        DB[("SQLite database data.db")]
    end

    %% Processing Subsystems
    subgraph Engine [Inference & Video Rendering Engine]
        K[YOLOv8 ONNX Model best.onnx]
        L["OpenCV VideoWriter AVC1/H.264"]
        M[FFmpeg Subprocess HLS Stream]
        N[ThreadPool Executor Worker]
    end

    %% Data Flow
    A -->|POST image blob| F
    F -->|ONNX Inference| K
    K -->|Returns JSON detections| D
    
    B -->|POST video file| G
    G -->|Submit to ThreadPool| N
    N -->|Process frames| K
    N -->|Save alert metadata| DB
    N -->|Output HLS stream| M
    N -->|Save MP4 file| L
    
    M -->|Stream HLS chunks| C
    C -->|GET task status polling| H
    H -->|Query DB| DB
    
    C -->|Downloads MP4 file| J
    I -->|Streams final MP4| C
```

### Data Pipeline Mechanics
1. **Accelerated Inference & Bounding Overlays**: The client grabs video frames via `getUserMedia` at an interval of `150ms`, rendering them to an offscreen HTML5 `canvas` element. The raw pixel arrays are converted into a JPEG blob and POSTed to `/api/process-frame`. The backend decodes the bytes and performs inference using the optimized **YOLOv8 ONNX** model. It returns only raw coordinate metadata. The React client draws bounding boxes, class labels, and confidence tags on a transparent canvas overlay, saving CPU cycles and network bandwidth.
2. **Concurrency & Telemetry Persistence**: Under upload concurrency, Python-level video compiling is offloaded to a global thread pool using `ThreadPoolExecutor` to bypass event loop blocking. Task logs, progress, and detected alerts are written into a persistent local **SQLite Database** (`data.db`).
3. **Dynamic HLS Slicing**: As drone footage processes, the backend pipes raw frames into an `ffmpeg` subprocess that compiles and slices them on-the-fly into HTTP Live Streaming (HLS) formats (`playlist.m3u8` and `.ts` segments). The user can stream the annotated video segments immediately via `hls.js` while the task runs in the background. On completion, the frontend switches to the finalized `.mp4` file for high-performance seeking and download availability.
4. **Custom SVG Analytics Dashboard**: The right sidebar includes a toggle between the Alerts Log and the **Analytics Charts**. Interactive SVG components render defect type distributions (Bar Chart) and defect spatial density along the tunnel markers (Line Chart) to locate weak zones.

---

## Machine Learning Defect Classes

The YOLOv8 model is trained to identify and track four target concrete defects:
- **Class 0 (`crack`)**: Structural cracks indicating tensile stress.
- **Class 1 (`rebar`)**: Exposed structural reinforcement bars.
- **Class 2 (`spalling`)**: Flaking or breaking off of concrete chunks.
- **Class 3 (`unexposed bar`)**: Subsurface structural elements showing signs of exposure.

---

## Local Installation & Setup

### Option A: Quickstart with Docker (Recommended)
This method orchestrates both services and compiles system libraries (FFmpeg, system codecs) automatically inside Docker containers.
1. Make sure Docker and Docker Compose are installed.
2. In the root workspace directory, run:
   ```bash
   docker-compose up --build
   ```
3. Open `http://localhost` in your browser. (The React client runs on port `80`, proxying API calls to the FastAPI container on port `8000`).

### Option B: Manual Setup

#### 1. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Compile the YOLO PyTorch model to ONNX:
   ```bash
   python -c "from ultralytics import YOLO; YOLO('best.pt').export(format='onnx', simplify=True)"
   ```
4. Download the OpenH264 binary (required by OpenCV for H.264 video compression on Windows):
   ```bash
   python get_openh264.py
   ```
5. Start the FastAPI application server:
   ```bash
   python app.py
   ```
   *The backend will run on http://localhost:8000.*

#### 2. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend client will run on http://localhost:5173.*
