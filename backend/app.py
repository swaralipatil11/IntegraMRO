"""
MRO Vision Control API - Core Application Server
Developer Notes:
- Thread Safety: YOLOv8 is not inherently thread-safe for concurrent predictions. A model mutex lock 
  ('model_lock') is used to serialize inference calls across webcam and background video queues.
- Asynchronous Workers: Video processing is handled asynchronously via ThreadPoolExecutor. Raw frames 
  are piped to FFmpeg in real-time to generate HLS streams, allowing the client to watch processing logs.
- Memory Control: File chunks are processed using 1MB streams, and telemetry exports are compiled 
  entirely in-memory via io.StringIO to minimize edge-disk write cycles and SSD wear.
"""
import os
import uuid
import time
import base64
import cv2
import numpy as np
import subprocess
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from ultralytics import YOLO
import csv
import io

# Import persistence layer
from database import save_task, get_task, add_anomaly

# Create absolute directory paths relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_VIDEOS_DIR = os.path.join(BASE_DIR, "static", "videos")
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, "temp_uploads")

# Create directories
os.makedirs(STATIC_VIDEOS_DIR, exist_ok=True)
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

# Verify FFmpeg availability on startup
if not shutil.which("ffmpeg"):
    print("WARNING: 'ffmpeg' executable not found in system PATH.")
    print("Drone video transcoding and HLS stream segmenting will fail.")

app = FastAPI(title="Concrete Defect Detection API")

# Configure CORS to allow frontend connections
# Set allow_credentials to False when allow_origins is wildcard to prevent Starlette crash
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for production security
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves static files (processed videos and HLS streams)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Load custom YOLO model (compile to ONNX if needed)
MODEL_PT_PATH = os.path.join(BASE_DIR, "best.pt")
MODEL_ONNX_PATH = os.path.join(BASE_DIR, "best.onnx")

if not os.path.exists(MODEL_PT_PATH):
    raise RuntimeError(f"Model file '{MODEL_PT_PATH}' not found. Please place it in the workspace directory.")

if not os.path.exists(MODEL_ONNX_PATH):
    print("ONNX model not found. Compiling from PyTorch weights...")
    try:
        pt_model = YOLO(MODEL_PT_PATH)
        pt_model.export(format="onnx", simplify=True)
        print("Model compiled to ONNX successfully.")
    except Exception as e:
        print(f"Failed to compile model to ONNX: {e}. Falling back to PyTorch.")

# If ONNX weights exist, use them; otherwise, fall back to PT
active_model_path = MODEL_ONNX_PATH if os.path.exists(MODEL_ONNX_PATH) else MODEL_PT_PATH
print(f"Loading YOLO model from: {active_model_path}...")
model = YOLO(active_model_path, task="detect")
print("YOLO model loaded successfully.")

# ThreadPoolExecutor to handle CPU-bound inference in separate threads
# This controls concurrency and prevents GIL blocking since ORT/OpenCV release the GIL
executor = ThreadPoolExecutor(max_workers=2)

# Lock to serialize concurrent YOLO model inferences (YOLO is not thread-safe)
import threading
model_lock = threading.Lock()

def process_video_background(task_id: str, input_path: str, output_filename: str):
    save_task(task_id, "processing", 0)
    
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        save_task(task_id, "failed", error="Failed to open uploaded video file")
        if os.path.exists(input_path):
            os.remove(input_path)
        return
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames <= 0:
        total_frames = 1
        
    # Paths for outputs using absolute static directory
    output_mp4_path = os.path.join(STATIC_VIDEOS_DIR, output_filename)
    temp_output_mp4_path = output_mp4_path + ".raw.mp4"
    hls_dir = os.path.join(STATIC_VIDEOS_DIR, task_id)
    os.makedirs(hls_dir, exist_ok=True)
    hls_playlist = os.path.join(hls_dir, "playlist.m3u8")
    
    # 1. Setup OpenCV VideoWriter for the raw temporary MP4 file
    # We will write frames to a raw file first, and later optimize it using FFmpeg for web streaming.
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(temp_output_mp4_path, fourcc, fps, (width, height))
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_output_mp4_path, fourcc, fps, (width, height))
        
    # 2. Setup FFmpeg subprocess pipe for real-time HLS segmenting
    # Raw BGR24 frames written to stdin are compiled and segmented directly into HLS
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-g", str(fps * 2),  # Keyframe interval every 2 seconds
        "-hls_time", "2",
        "-hls_list_size", "0",
        "-hls_playlist_type", "event",
        "-hls_segment_filename", os.path.join(hls_dir, "seg_%03d.ts"),
        hls_playlist
    ]
    
    ffmpeg_proc = None
    try:
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, bufsize=10**8)
    except Exception as ffmpeg_err:
        print(f"Warning: Failed to initialize FFmpeg HLS streaming subprocess: {ffmpeg_err}")

    frame_idx = 0
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            start_time = time.time()
            
            # Run YOLO ONNX inference inside the thread-safe lock
            with model_lock:
                results = model(frame, verbose=False, conf=0.30)[0]
            
            latency_ms = (time.time() - start_time) * 1000
            fps_display = 1000 / latency_ms if latency_ms > 0 else fps
            
            # Look for defects and record them in the SQLite DB
            if len(results.boxes) > 0:
                for box in results.boxes:
                    cls_idx = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    class_name = model.names[cls_idx]
                    
                    # Generate simulated telemetry payload
                    simulated_tunnel_marker = round(15.2 + (frame_idx * 0.12), 2)
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    add_anomaly(
                        task_id=task_id,
                        timestamp=timestamp_str,
                        class_name=class_name,
                        confidence=round(conf, 3),
                        bbox=xyxy,
                        frame_index=frame_idx,
                        estimated_position=simulated_tunnel_marker
                    )
            
            # Generate prediction annotations over the frame for the saved file outputs
            annotated_frame = results.plot()
            
            # Overlay dashboard HUD
            cv2.putText(annotated_frame, "PAYLOAD: MRO_VISION_CAM_01", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
            cv2.putText(annotated_frame, f"THROUGHPUT: {fps_display:.1f} FPS", (30, 95),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
            cv2.putText(annotated_frame, f"LATENCY: {latency_ms:.1f} ms", (30, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
            cv2.putText(annotated_frame, f"FRAME METRIC INDEX: {frame_idx}", (30, 185),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
            
            # Write to MP4 file
            out.write(annotated_frame)
            
            # Write raw bytes to FFmpeg pipe for dynamic HLS stream
            if ffmpeg_proc and ffmpeg_proc.stdin:
                try:
                    ffmpeg_proc.stdin.write(annotated_frame.tobytes())
                except Exception as pipe_err:
                    print(f"FFmpeg stdin write error: {pipe_err}")
                    
            frame_idx += 1
            
            # Update progress status in database every 10 frames to avoid DB locks
            if frame_idx % 10 == 0 or frame_idx == total_frames:
                progress_pct = min(99, int((frame_idx / total_frames) * 100))
                save_task(task_id, "processing", progress_pct)
            
        cap.release()
        out.release()
        
        # Finalize and close HLS pipeline
        if ffmpeg_proc:
            if ffmpeg_proc.stdin:
                ffmpeg_proc.stdin.close()
            ffmpeg_proc.wait()
            
        # Post-process the raw MP4 to compile browser-compatible H264 with +faststart (MOOV atom at front)
        try:
            h264_temp_path = output_mp4_path + ".h264.mp4"
            ffmpeg_convert_cmd = [
                "ffmpeg", "-y",
                "-i", temp_output_mp4_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                h264_temp_path
            ]
            subprocess.run(ffmpeg_convert_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(h264_temp_path):
                os.replace(h264_temp_path, output_mp4_path)
                if os.path.exists(temp_output_mp4_path):
                    os.remove(temp_output_mp4_path)
        except Exception as conv_err:
            print(f"Warning: Failed to optimize MP4 with FFmpeg: {conv_err}")
            # Fallback: rename raw file if optimization failed
            if os.path.exists(temp_output_mp4_path) and not os.path.exists(output_mp4_path):
                os.rename(temp_output_mp4_path, output_mp4_path)
        
        # Cleanup temporary input file
        if os.path.exists(input_path):
            os.remove(input_path)
            
        # Update completed state in DB
        save_task(task_id, "completed", 100, video_url=f"/static/videos/{task_id}/playlist.m3u8", fps=fps)
        
    except Exception as e:
        cap.release()
        if 'out' in locals():
            out.release()
        if ffmpeg_proc:
            try:
                if ffmpeg_proc.stdin:
                    ffmpeg_proc.stdin.close()
                ffmpeg_proc.wait()
            except:
                pass
        # Cleanup temporary outputs on failure
        if os.path.exists(temp_output_mp4_path):
            try:
                os.remove(temp_output_mp4_path)
            except:
                pass
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except:
                pass
                
        save_task(task_id, "failed", error=str(e))

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    # Verify file is a video
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a video.")
        
    # Generate unique ID
    task_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] or ".mp4"
    temp_input_filename = f"{task_id}_input{file_ext}"
    temp_input_path = os.path.join(TEMP_UPLOADS_DIR, temp_input_filename)
    
    # Save video locally to temp space in chunks to prevent memory bloat
    try:
        with open(temp_input_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")
        
    output_filename = f"{task_id}_processed.mp4"
    
    # Submit the CPU-bound video processing task to the executor pool
    executor.submit(process_video_background, task_id, temp_input_path, output_filename)
    
    return {"task_id": task_id, "status": "processing"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/process-frame")
async def process_frame(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")
        
    try:
        # Read uploaded image bytes
        image_bytes = await file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise HTTPException(status_code=400, detail="Failed to decode image frame")
            
        height, width = frame.shape[:2]
        start_time = time.time()
        
        # Inference with YOLOv8 ONNX model inside the thread-safe lock
        with model_lock:
            results = model(frame, verbose=False, conf=0.30)[0]
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Parse defects info (sending coordinates only, avoiding heavy Base64 image payload)
        detections = []
        if len(results.boxes) > 0:
            for box in results.boxes:
                cls_idx = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                class_name = model.names[cls_idx]
                
                detections.append({
                    "class": class_name,
                    "confidence": round(conf, 3),
                    "bbox": [round(c, 1) for c in xyxy]
                })
        
        return {
            "detections": detections,
            "latency_ms": round(latency_ms, 1),
            "width": width,
            "height": height
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame processing error: {str(e)}")

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "device": str(model.device),
        "classes": model.names
    }

@app.get("/api/videos/{task_id}")
async def get_video_display(task_id: str):
    filename = f"{task_id}_processed.mp4"
    filepath = os.path.join(STATIC_VIDEOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Processed video not found")
    
    # FileResponse supports HTTP range requests automatically (needed for Chrome/Safari video seeking)
    return FileResponse(filepath, media_type="video/mp4")

@app.get("/api/videos/{task_id}/download")
async def download_video(task_id: str):
    filename = f"{task_id}_processed.mp4"
    filepath = os.path.join(STATIC_VIDEOS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Processed video not found")
        
    return FileResponse(
        filepath, 
        media_type="video/mp4", 
        filename=f"processed_inspection_{task_id[:8]}.mp4"
    )

@app.get("/api/tasks/{task_id}/export")
async def export_task_csv(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Frame Index", 
        "Timestamp", 
        "Detected Class", 
        "Confidence Score", 
        "Estimated Tunnel Position (m)", 
        "Sensor ID",
        "Bounding Box [x1, y1, x2, y2]"
    ])
    
    for r in task.get("results", []):
        meta = r.get("defect_metadata", {})
        telemetry = r.get("payload_telemetry", {})
        writer.writerow([
            r.get("frame_index"),
            r.get("timestamp"),
            meta.get("detected_class"),
            meta.get("confidence_score"),
            telemetry.get("estimated_tunnel_position_m"),
            telemetry.get("sensor_id"),
            str(meta.get("bounding_box_xyxy", []))
        ])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inspection_report_{task_id[:8]}.csv"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

