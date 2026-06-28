# --- CELL 0 ---
pip install ultralytics roboflow opencv-python matplotlib

# --- CELL 1 ---
# Cell 1: Import dependencies and verify hardware acceleration
import os
import torch
from ultralytics import YOLO
from roboflow import Roboflow

# Check if GPU is available locally
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# --- CELL 2 ---
# Cell 2 (Fixed): Pull a Verified Public Concrete Defect Dataset
import os
import shutil
from roboflow import Roboflow

# 1. Wipe out any previous failed download attempts to clear memory
bad_folder = "./concrete-defect-object-recognition-1"
if os.path.exists(bad_folder):
    shutil.rmtree(bad_folder)
    print("Cleared out corrupted files.")

# 2. Initialize Roboflow with your API key
rf = Roboflow(api_key="iBU4YXHh3MDLE69qF84P")

# 3. Pull a public dataset that is already perfectly formatted for YOLOv8
# Workspace: concrete-defect-recognition | Project: concrete-defect-object-recognition | Version: 1
project = rf.workspace("concrete-defect-recognition").project("concrete-defect-object-recognition")

try:
    print("Downloading stable public concrete defect dataset...")
    dataset = project.version(1).download("yolov8")
    print(f"\n[SUCCESS] Dataset downloaded locally to: {dataset.location}")
except Exception as e:
    print(f"\n[ERROR] Download failed. Error details: {e}")

# --- CELL 3 ---
# Cell 3: Initialize and train the YOLOv8 Nano model
import os
import torch
from ultralytics import YOLO

# 1. Check for local hardware acceleration (CUDA)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Executing training on: {device.upper()}")
if device == "cuda":
    print(f"GPU Device Name: {torch.cuda.get_device_name(0)}")

# 2. Load the ultra-lightweight nano model pre-trained on COCO
model = YOLO("yolov8n.pt")

# 3. Path to the data.yaml file downloaded by Roboflow
# Using 'dataset' variable from the successful cell block
yaml_path = os.path.join(dataset.location, "data.yaml")

# 4. Kick off the training loop
results = model.train(
    data=yaml_path,
    epochs=30,      # Perfect sweet spot for a Day 1 sprint baseline
    imgsz=640,
    batch=16,
    device=device,
    name="concrete_baseline_yolov8n"
)

# --- CELL 4 ---
import os

# Walk through the directory to find where the .pt files were saved
print("--- SEARCHING FOR YOUR TRAINED WEIGHTS ---")
for root, dirs, files in os.walk("/content/runs"):
    for file in files:
        if file.endswith(".pt"):
            print(f"Found weights file at: {os.path.join(root, file)}")

# --- CELL 5 ---
from google.colab import files

# Directly triggers a browser download for your best weights
files.download('/content/runs/detect/concrete_baseline_yolov8n/weights/best.pt')

# --- CELL 6 ---
# Day 2 - Cell 1: Export Custom YOLOv8 Model to ONNX Format
import os
from ultralytics import YOLO

# 1. Path to your downloaded weights file
weights_path = "./best.pt"

if not os.path.exists(weights_path):
    print(f"[ERROR] '{weights_path}' not found. Please ensure your downloaded weights are in this folder!")
else:
    # 2. Load your custom trained model
    model = YOLO(weights_path)

    # 3. Export the model to ONNX format with graph simplification enabled
    print("Converting model to ONNX format for edge deployment...")
    onnx_path = model.export(format="onnx", simplify=True)

    print(f"\n[SUCCESS] Model successfully exported to: {onnx_path}")

# --- CELL 7 ---
import os
print("Your notebook is running in:")
print(os.getcwd())

print("\nFiles present in this folder:")
print(os.listdir('.'))

# --- CELL 8 ---
# Day 2 - Cell 2: Pure CPU ONNX Runtime Benchmarking (Bypassing AutoUpdate Bug)
import time
import numpy as np
import onnxruntime as ort
from ultralytics import YOLO

# 1. Setup paths and mock verification frame
weights_pt = "./best.pt"
weights_onnx = "./best.onnx"

# 640x640 is the exact image size our model was trained on
dummy_frame_pt = np.zeros((640, 640, 3), dtype=np.uint8)

print("=== STARTING HARDWARE CO-DESIGN BENCHMARK ===")

# --- PART 1: PROFILE PYTORCH BASELINE ---
print("\nProfiling local PyTorch baseline latency (50 iterations)...")
pt_model = YOLO(weights_pt)

start_time = time.time()
for _ in range(50):
    pt_model(dummy_frame_pt, verbose=False)
pt_latency = (time.time() - start_time) / 50 * 1000  # Average time in milliseconds
pt_fps = 1000 / pt_latency

# --- PART 2: PROFILE NATIVE CPU ONNX RUNTIME ---
print("Profiling Native CPU ONNX Runtime latency (50 iterations)...")

# Force ONNX Runtime to use an optimized multi-threaded CPU execution pool explicitly
session_options = ort.SessionOptions()
session_options.intra_op_num_threads = 4  # Spreads the matrix math across 4 CPU cores
session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

# Initialize session safely using the explicit CPU provider
ort_session = ort.InferenceSession(weights_onnx, session_options, providers=['CPUExecutionProvider'])

# Prepare dummy input matching the ONNX model requirement: shape (1, 3, 640, 640), float32 scaled 0.0-1.0
input_name = ort_session.get_inputs()[0].name
dummy_frame_onnx = np.zeros((1, 3, 640, 640), dtype=np.float32)

start_time = time.time()
for _ in range(50):
    ort_session.run(None, {input_name: dummy_frame_onnx})
onnx_latency = (time.time() - start_time) / 50 * 1000
onnx_fps = 1000 / onnx_latency

# --- PART 3: PRINT METRICS RESULTS ---
print("\n========== TRUE CPU BENCHMARK METRICS ==========")
print(f"PyTorch Local Latency: {pt_latency:.2f} ms | Speed: {pt_fps:.1f} FPS")
print(f"ONNX CPU Local Latency:{onnx_latency:.2f} ms | Speed: {onnx_fps:.1f} FPS")
print("================================================")

# --- CELL 9 ---
!pip uninstall -y onnxruntime-gpu
!pip install onnxruntime

# --- CELL 10 ---
# Day 3: Real-Time Robotic Inspection Video Pipeline Simulation
import cv2
import os
import time
from ultralytics import YOLO

# 1. Initialize your custom object detection engine
weights_path = "./best.pt"
input_video_path = "inspection.mp4"  # Make sure your uploaded file matches this name exactly!
output_video_path = "processed_robotic_inspection.mp4"

if not os.path.exists(weights_path):
    print(f"[ERROR] '{weights_path}' not found in the current directory.")
elif not os.path.exists(input_video_path):
    print(f"[WARNING] '{input_video_path}' not found in your files sidebar.")
    print("Please upload a 5-10 second inspection clip to your left sidebar and rename it to 'inspection.mp4'.")
else:
    # 2. Initialize the weights structure
    model = YOLO(weights_path)

    # 3. Setup OpenCV Video Readers and Writers
    cap = cv2.VideoCapture(input_video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = int(cap.get(cv2.CAP_PROP_FPS))

    # Using 'mp4v' codec for seamless local browser playback compatibility
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    print("🚀 Initializing continuous frame processing stream...")
    frame_count = 0

    # 4. Core Frame-by-Frame Processing Loop
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # End of video stream sequence reached

        start_time = time.time()

        # Run inference frame-by-frame
        # Setting a confidence threshold of 0.40 to prevent false-positive tracking noise
        results = model(frame, verbose=False, conf=0.40)[0]

        # Calculate localized computational metrics
        latency_ms = (time.time() - start_time) * 1000
        fps_display = 1000 / latency_ms

        # Generate prediction boundary masks over the frame
        annotated_frame = results.plot()

        # Overlay mission control telemetry onto the top-left section of each frame
        cv2.putText(annotated_frame, "PAYLOAD: MRO_VISION_CAM_01", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)  # High-vis layout green
        cv2.putText(annotated_frame, f"THROUGHPUT: {fps_display:.1f} FPS", (30, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
        cv2.putText(annotated_frame, f"LATENCY: {latency_ms:.1f} ms", (30, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)
        cv2.putText(annotated_frame, f"FRAME METRIC INDEX: {frame_count}", (30, 185),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (56, 208, 86), 2)

        # Append the processed frame to our compiled output clip
        out.write(annotated_frame)
        frame_count += 1

    # 5. Resource Release Protocols
    cap.release()
    out.release()
    print(f"\n[SUCCESS] Continuous stream simulation compiled successfully!")
    print(f"📁 Refresh your folder sidebar and download: '{output_video_path}' to inspect the results.")

# --- CELL 11 ---
# Day 4: Industrial Edge Telemetry & JSON Logging Pipeline
import json
import os
import time
import random
from datetime import datetime
from ultralytics import YOLO
import cv2

# 1. Initialize file paths
weights_path = "./best.pt"
video_path = "inspection.mp4"
log_file_path = "telemetry_alerts.json"

# Clear out old test logs if they exist to keep the dataset clean
if os.path.exists(log_file_path):
    os.remove(log_file_path)

def append_to_telemetry_stream(class_name, confidence, bbox, frame_idx, log_path=log_file_path):
    """Encapsulates raw frame detections into standard industrial JSON packets."""
    # Simulate a 100-meter tunnel patrol where the video frames map to positions
    simulated_tunnel_marker = round(15.2 + (frame_idx * 0.12), 2)

    telemetry_packet = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "system_status": "ALERT_TRIGGERED",
        "payload_telemetry": {
            "estimated_tunnel_position_m": simulated_tunnel_marker,
            "sensor_id": "MRO_VISION_CAM_01"
        },
        "defect_metadata": {
            "detected_class": class_name,
            "confidence_score": round(float(confidence), 3),
            "bounding_box_xyxy": [round(float(coord), 1) for coord in bbox]
        }
    }

    # Read existing stream array or initialize a clean list
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                log_data = json.load(f)
        except json.JSONDecodeError:
            log_data = []
    else:
        log_data = []

    log_data.append(telemetry_packet)
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=4)

# 2. Run the processing engine to build the telemetry logs
if not os.path.exists(weights_path) or not os.path.exists(video_path):
    print("[ERROR] Ensure both 'best.pt' and 'inspection_input.mp4.mp4' exist in your workspace!")
else:
    model = YOLO(weights_path)
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    alerts_logged = 0

    print("📡 Activating Telemetry Logging Engine...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Run model frame-by-frame
        # Setting conf to 0.30 to ensure it tightly catches the crack from your video
        results = model(frame, verbose=False, conf=0.30)[0]

        if len(results.boxes) > 0:
            for box in results.boxes:
                cls_idx = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                class_label = model.names[cls_idx]

                # Send straight to the backend telemetry automation logging pool
                append_to_telemetry_stream(class_label, conf, xyxy, frame_count)
                alerts_logged += 1

        frame_count += 1

    cap.release()
    print(f"\n[SUCCESS] Engine offline. Scanned {frame_count} frames and successfully compiled {alerts_logged} anomaly packets into '{log_file_path}'!")

# --- CELL 12 ---

