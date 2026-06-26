import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Enable WAL mode for concurrent write resilience
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        progress INTEGER DEFAULT 0,
        video_url TEXT,
        fps INTEGER,
        error TEXT,
        created_at TEXT NOT NULL
    )
    """)
    
    # Create anomalies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anomalies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        class_name TEXT NOT NULL,
        confidence REAL NOT NULL,
        bbox_x1 REAL NOT NULL,
        bbox_y1 REAL NOT NULL,
        bbox_x2 REAL NOT NULL,
        bbox_y2 REAL NOT NULL,
        frame_index INTEGER NOT NULL,
        estimated_position REAL NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def save_task(task_id: str, status: str, progress: int = 0, video_url: str = None, fps: int = None, error: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
    INSERT INTO tasks (id, status, progress, video_url, fps, error, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        status = excluded.status,
        progress = excluded.progress,
        video_url = COALESCE(excluded.video_url, tasks.video_url),
        fps = COALESCE(excluded.fps, tasks.fps),
        error = COALESCE(excluded.error, tasks.error)
    """, (task_id, status, progress, video_url, fps, error, now_str))
    
    conn.commit()
    conn.close()

def get_task(task_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    
    if not task:
        conn.close()
        return None
        
    task_dict = dict(task)
    
    # Fetch associated anomalies
    cursor.execute("SELECT * FROM anomalies WHERE task_id = ? ORDER BY frame_index ASC", (task_id,))
    anomalies = cursor.fetchall()
    
    results = []
    for anomaly in anomalies:
        results.append({
            "timestamp": anomaly["timestamp"],
            "system_status": "ALERT_TRIGGERED",
            "payload_telemetry": {
                "estimated_tunnel_position_m": anomaly["estimated_position"],
                "sensor_id": "MRO_VISION_CAM_01"
            },
            "defect_metadata": {
                "detected_class": anomaly["class_name"],
                "confidence_score": anomaly["confidence"],
                "bounding_box_xyxy": [anomaly["bbox_x1"], anomaly["bbox_y1"], anomaly["bbox_x2"], anomaly["bbox_y2"]]
            },
            "frame_index": anomaly["frame_index"]
        })
        
    task_dict["results"] = results
    conn.close()
    return task_dict

def add_anomaly(task_id: str, timestamp: str, class_name: str, confidence: float, bbox: list, frame_index: int, estimated_position: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO anomalies (task_id, timestamp, class_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2, frame_index, estimated_position)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (task_id, timestamp, class_name, confidence, bbox[0], bbox[1], bbox[2], bbox[3], frame_index, estimated_position))
    
    conn.commit()
    conn.close()

# Initialize on import
init_db()
