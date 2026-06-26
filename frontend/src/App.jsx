import React, { useState, useRef, useEffect } from 'react';
import Hls from 'hls.js';
import './App.css';

const getApiBaseUrl = () => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return `${window.location.protocol}//${window.location.hostname}:8000`;
};

const API_BASE_URL = getApiBaseUrl();

// Helper components for Custom SVG Analytics Charts
function DefectBarChart({ counts }) {
  const data = [
    { label: 'CRK', value: counts.crack || 0, color: 'var(--accent-green)' },
    { label: 'RBR', value: counts.rebar || 0, color: 'var(--accent-blue)' },
    { label: 'SPL', value: counts.spalling || 0, color: 'var(--accent-red)' },
    { label: 'UXB', value: counts['unexposed bar'] || 0, color: 'var(--accent-yellow)' },
  ];
  
  const maxVal = Math.max(...data.map(d => d.value), 1);
  const chartHeight = 120;
  const chartWidth = 320;
  const padding = 25;
  
  return (
    <div className="chart-wrapper">
      <h4 className="chart-title">DEFECT TYPE DISTRIBUTION</h4>
      <svg width="100%" height={chartHeight + padding} viewBox={`0 0 ${chartWidth} ${chartHeight + padding}`} style={{ overflow: 'visible' }}>
        {/* Draw background grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => (
          <line 
            key={idx}
            x1="20"
            y1={chartHeight - ratio * chartHeight}
            x2={chartWidth - 20}
            y2={chartHeight - ratio * chartHeight}
            stroke="rgba(255, 255, 255, 0.05)"
            strokeDasharray="2"
          />
        ))}
        {/* Draw bars */}
        {data.map((item, idx) => {
          const barWidth = 40;
          const spacing = (chartWidth - 40) / 4;
          const x = 30 + idx * spacing;
          const h = (item.value / maxVal) * (chartHeight - 10);
          const y = chartHeight - h;
          
          return (
            <g key={idx}>
              {/* Bar shadow/glow */}
              {h > 0 && (
                <rect 
                  x={x} 
                  y={y} 
                  width={barWidth} 
                  height={h} 
                  fill={item.color} 
                  opacity="0.1" 
                />
              )}
              {/* Bar itself */}
              <rect 
                x={x} 
                y={y} 
                width={barWidth} 
                height={h} 
                fill={item.color} 
                rx="3"
                style={{ transition: 'all 0.5s ease' }}
              />
              {/* Value label */}
              <text 
                x={x + barWidth / 2} 
                y={y - 6} 
                fill="var(--text-primary)" 
                fontSize="10" 
                fontWeight="bold"
                textAnchor="middle"
                fontFamily="var(--font-hud)"
              >
                {item.value}
              </text>
              {/* Label axis */}
              <text 
                x={x + barWidth / 2} 
                y={chartHeight + 15} 
                fill="var(--text-secondary)" 
                fontSize="10" 
                textAnchor="middle"
                fontFamily="var(--font-hud)"
              >
                {item.label}
              </text>
            </g>
          );
        })}
        {/* Base axis line */}
        <line x1="20" y1={chartHeight} x2={chartWidth - 20} y2={chartHeight} stroke="rgba(255, 255, 255, 0.2)" />
      </svg>
    </div>
  );
}

function SpatialLineChart({ data }) {
  if (data.length === 0) {
    return (
      <div className="chart-wrapper">
        <h4 className="chart-title">STRUCTURAL DEFECT SPATIAL DENSITY</h4>
        <div className="chart-empty-state">Awaiting telemetry data...</div>
      </div>
    );
  }
  
  const chartHeight = 100;
  const chartWidth = 320;
  const maxVal = Math.max(...data.map(d => d.value), 1);
  
  const points = data.map((item, idx) => {
    const spacing = (chartWidth - 40) / (data.length - 1 || 1);
    const x = 20 + idx * spacing;
    const y = chartHeight - (item.value / maxVal) * (chartHeight - 15);
    return { x, y, label: item.label, value: item.value };
  });
  
  const pathData = points.reduce((acc, p, idx) => {
    return acc + `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`;
  }, '');
  
  const areaData = points.length > 0 
    ? `${pathData} L ${points[points.length - 1].x} ${chartHeight} L ${points[0].x} ${chartHeight} Z`
    : '';

  return (
    <div className="chart-wrapper">
      <h4 className="chart-title">STRUCTURAL DEFECT SPATIAL DENSITY</h4>
      <svg width="100%" height={chartHeight + 25} viewBox={`0 0 ${chartWidth} ${chartHeight + 25}`} style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="lineGlow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-red)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="var(--accent-red)" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        
        {/* Draw horizontal grid lines */}
        {[0, 0.5, 1].map((ratio, idx) => (
          <line 
            key={idx}
            x1="20"
            y1={chartHeight - ratio * chartHeight}
            x2={chartWidth - 20}
            y2={chartHeight - ratio * chartHeight}
            stroke="rgba(255, 255, 255, 0.05)"
          />
        ))}
        
        {/* Filled Area */}
        {points.length > 0 && (
          <path d={areaData} fill="url(#lineGlow)" style={{ transition: 'all 0.5s ease' }} />
        )}
        
        {/* Main Line */}
        {points.length > 0 && (
          <path 
            d={pathData} 
            fill="none" 
            stroke="var(--accent-red)" 
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transition: 'all 0.5s ease', filter: 'drop-shadow(0 0 3px var(--accent-red))' }}
          />
        )}
        
        {/* Draw points */}
        {points.map((p, idx) => (
          <g key={idx}>
            <circle 
              cx={p.x} 
              cy={p.y} 
              r={p.value > 0 ? "4" : "2"} 
              fill={p.value > 0 ? "var(--accent-red)" : "rgba(255, 255, 255, 0.2)"} 
              stroke="var(--bg-primary)"
              strokeWidth="1.5"
            />
            {p.value > 0 && (
              <text 
                x={p.x} 
                y={p.y - 8} 
                fill="var(--accent-red)" 
                fontSize="8" 
                fontWeight="bold"
                textAnchor="middle"
                fontFamily="var(--font-hud)"
              >
                {p.value}
              </text>
            )}
            {idx % 2 === 0 && (
              <text 
                x={p.x} 
                y={chartHeight + 15} 
                fill="var(--text-secondary)" 
                fontSize="8" 
                textAnchor="middle"
                fontFamily="var(--font-hud)"
              >
                {p.label}m
              </text>
            )}
          </g>
        ))}
        {/* Base axis line */}
        <line x1="20" y1={chartHeight} x2={chartWidth - 20} y2={chartHeight} stroke="rgba(255, 255, 255, 0.2)" />
      </svg>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('webcam'); // 'webcam' or 'upload'
  const [sidebarTab, setSidebarTab] = useState('logs'); // 'logs' or 'charts'
  
  // Webcam states
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [liveDetections, setLiveDetections] = useState([]);
  const [liveLog, setLiveLog] = useState([]);
  const [cameraError, setCameraError] = useState(null);
  const [liveMetrics, setLiveMetrics] = useState({ fps: 0, latency: 0, frameCount: 0 });

  // Video upload states
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [taskId, setTaskId] = useState(null);
  const [processedVideoUrl, setProcessedVideoUrl] = useState(null);
  const [processedVideoFps, setProcessedVideoFps] = useState(30);
  const [videoAlerts, setVideoAlerts] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const videoPlayerRef = useRef(null);
  const webcamIntervalRef = useRef(null);
  const fileInputRef = useRef(null);
  const frameCountRef = useRef(0);

  // Hls.js instance state
  const [hlsInstance, setHlsInstance] = useState(null);

  // Health check and backend verification
  const [backendStatus, setBackendStatus] = useState('connecting');
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/health`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'healthy') {
          setBackendStatus('online');
        } else {
          setBackendStatus('error');
        }
      })
      .catch(() => {
        setBackendStatus('offline');
      });
  }, []);

  // ----------------------------------------------------
  // Live Webcam Logic
  // ----------------------------------------------------
  useEffect(() => {
    if (isCameraOn) {
      startWebcamStream();
    } else {
      stopWebcamStream();
    }

    return () => {
      stopWebcamStream();
    };
  }, [isCameraOn]);

  const startWebcamStream = async () => {
    setCameraError(null);
    frameCountRef.current = 0;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 640 }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        
        // Start processing interval loop (150ms for smooth client-overlay tracking)
        webcamIntervalRef.current = setInterval(captureAndProcessFrame, 150);
      }
    } catch (err) {
      console.error("Camera access error:", err);
      setCameraError("Unable to access the webcam. Please ensure permissions are granted.");
      setIsCameraOn(false);
    }
  };

  const stopWebcamStream = () => {
    if (webcamIntervalRef.current) {
      clearInterval(webcamIntervalRef.current);
      webcamIntervalRef.current = null;
    }
    
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    
    setLiveDetections([]);
    setLiveMetrics({ fps: 0, latency: 0, frameCount: 0 });
    
    // Clear overlay canvas
    if (overlayCanvasRef.current) {
      const ctx = overlayCanvasRef.current.getContext('2d');
      ctx.clearRect(0, 0, overlayCanvasRef.current.width, overlayCanvasRef.current.height);
    }
  };

  const drawDetections = (detections, videoEl, canvasEl) => {
    if (!videoEl || !canvasEl) return;
    const ctx = canvasEl.getContext('2d');
    
    // Dynamically align the canvas overlay coordinates over the video feed bounds
    canvasEl.style.position = 'absolute';
    canvasEl.style.left = `${videoEl.offsetLeft}px`;
    canvasEl.style.top = `${videoEl.offsetTop}px`;
    canvasEl.style.width = `${videoEl.clientWidth}px`;
    canvasEl.style.height = `${videoEl.clientHeight}px`;
    canvasEl.width = videoEl.videoWidth || 640;
    canvasEl.height = videoEl.videoHeight || 640;
    
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    
    if (!detections || detections.length === 0) return;
    
    detections.forEach(det => {
      const [x1, y1, x2, y2] = det.bbox;
      const w = x2 - x1;
      const h = y2 - y1;
      
      // Cyber HUD styling colors matching backend categories
      let color = '#38d056'; // Green default (crack)
      if (det.class === 'rebar') {
        color = '#58a6ff'; // Blue
      } else if (det.class === 'spalling') {
        color = '#ff5f40'; // Red
      } else if (det.class === 'unexposed bar') {
        color = '#f0883e'; // Orange
      }
      
      // Draw Bounding Box
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.strokeRect(x1, y1, w, h);
      
      // Draw Label Background
      ctx.fillStyle = color;
      ctx.font = 'bold 14px Orbitron, sans-serif';
      const labelText = `${det.class.toUpperCase()} ${(det.confidence * 100).toFixed(0)}%`;
      const textWidth = ctx.measureText(labelText).width;
      
      ctx.fillRect(x1 - 2, y1 - 22, textWidth + 8, 22);
      
      // Draw Label Text
      ctx.fillStyle = '#0a0e14';
      ctx.fillText(labelText, x1 + 2, y1 - 6);
    });
  };

  const captureAndProcessFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (!video || !canvas || video.readyState !== video.HAVE_ENOUGH_DATA) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      
      const formData = new FormData();
      formData.append('file', blob, 'frame.jpg');
      
      try {
        const startTime = performance.now();
        const response = await fetch(`${API_BASE_URL}/api/process-frame`, {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) throw new Error("Frame upload failed");
        
        const data = await response.json();
        const endTime = performance.now();
        
        const totalLatency = endTime - startTime;
        const currentFps = 1000 / totalLatency;
        
        setLiveDetections(data.detections || []);
        
        // Dynamic client-side overlay rendering
        drawDetections(data.detections || [], video, overlayCanvasRef.current);
        
        frameCountRef.current += 1;
        setLiveMetrics(prev => ({
          fps: currentFps,
          latency: data.latency_ms,
          frameCount: frameCountRef.current
        }));

        if (data.detections && data.detections.length > 0) {
          const timestamp = new Date().toLocaleTimeString();
          const newAlerts = data.detections.map(det => ({
            id: uuidv4(),
            timestamp,
            class: det.class,
            confidence: det.confidence,
            position: (15.2 + (frameCountRef.current * 0.12)).toFixed(2)
          }));
          setLiveLog(prev => [...newAlerts, ...prev].slice(0, 50));
        }
      } catch (err) {
        console.error("Frame processing error:", err);
      }
    }, 'image/jpeg', 0.8);
  };

  const uuidv4 = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  // ----------------------------------------------------
  // Video Upload & HLS Stream Logic
  // ----------------------------------------------------
  // Setup HLS player streaming while task compiles in background
  useEffect(() => {
    const video = videoPlayerRef.current;
    if (!video || !taskId || !processing) {
      if (hlsInstance) {
        hlsInstance.destroy();
        setHlsInstance(null);
      }
      return;
    }
    
    const streamUrl = `${API_BASE_URL}/static/videos/${taskId}/playlist.m3u8`;
    let hls;
    
    if (Hls.isSupported()) {
      hls = new Hls({
        maxMaxBufferLength: 8,
        liveSyncDurationCount: 2,
        enableWorker: true
      });
      hls.loadSource(streamUrl);
      hls.attachMedia(video);
      
      hls.on(Hls.Events.ERROR, function (event, data) {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
              break;
          }
        }
      });
      
      setHlsInstance(hls);
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl;
    }
    
    return () => {
      if (hls) {
        hls.destroy();
        setHlsInstance(null);
      }
    };
  }, [taskId, processing]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('video/')) {
        setSelectedFile(file);
        setUploadError(null);
      } else {
        setUploadError("Please upload a valid video file.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;
    
    setUploading(true);
    setUploadError(null);
    setProcessedVideoUrl(null);
    setVideoAlerts([]);
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/upload-video`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error("Failed to upload video to server");
      }
      
      const data = await response.json();
      setTaskId(data.task_id);
      setUploading(false);
      setProcessing(true);
      startPollingTask(data.task_id);
    } catch (err) {
      console.error(err);
      setUploadError(err.message || "An error occurred during upload.");
      setUploading(false);
    }
  };

  const startPollingTask = (taskId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
        if (!response.ok) throw new Error("Task status request failed");
        
        const data = await response.json();
        setUploadProgress(data.progress);
        
        // Grab streaming logs in real time as they arrive in SQLite DB
        if (data.results && data.results.length > 0) {
          setVideoAlerts(data.results);
        }
        
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setProcessing(false);
          setProcessedVideoUrl(`${API_BASE_URL}/static/videos/${taskId}_processed.mp4`);
          setProcessedVideoFps(data.fps || 30);
          setVideoAlerts(data.results);
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          setProcessing(false);
          setUploadError(data.error || "Background video processing failed.");
        }
      } catch (err) {
        console.error("Polling error:", err);
        clearInterval(pollInterval);
        setProcessing(false);
        setUploadError("Lost connection to the backend task status.");
      }
    }, 1000);
  };

  const handleLogClick = (alert) => {
    if (videoPlayerRef.current) {
      const seekTime = alert.frame_index / processedVideoFps;
      videoPlayerRef.current.currentTime = seekTime;
      videoPlayerRef.current.play();
    }
  };

  const resetUploadState = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setUploading(false);
    setProcessing(false);
    setTaskId(null);
    setProcessedVideoUrl(null);
    setVideoAlerts([]);
    setUploadError(null);
  };

  const defectCount = activeTab === 'webcam' 
    ? liveLog.length 
    : videoAlerts.length;

  // Aggregate statistics for custom SVG charts
  const getDefectCounts = () => {
    const alerts = activeTab === 'webcam' ? liveLog : videoAlerts;
    const counts = { crack: 0, rebar: 0, spalling: 0, 'unexposed bar': 0 };
    alerts.forEach(a => {
      const cls = activeTab === 'webcam' ? a.class : a.defect_metadata.detected_class;
      if (counts[cls] !== undefined) counts[cls]++;
    });
    return counts;
  };

  const getSpatialData = () => {
    const alerts = activeTab === 'webcam' ? liveLog : videoAlerts;
    if (alerts.length === 0) return [];
    
    const positions = alerts.map(a => {
      return activeTab === 'webcam' 
        ? parseFloat(a.position) 
        : a.payload_telemetry.estimated_tunnel_position_m;
    });
    
    const minPos = Math.min(...positions);
    const maxPos = Math.max(...positions);
    const range = maxPos - minPos;
    
    const binCount = 8;
    const bins = Array(binCount).fill(0);
    const step = range === 0 ? 1 : range / binCount;
    
    positions.forEach(pos => {
      const binIdx = range === 0 ? 0 : Math.min(binCount - 1, Math.floor((pos - minPos) / step));
      bins[binIdx]++;
    });
    
    return bins.map((val, idx) => ({
      label: (minPos + idx * step).toFixed(1),
      value: val
    }));
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <header className="app-header">
        <div className="brand-section">
          <svg className="logo-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
          </svg>
          <h1 className="brand-title">MRO VISION CONTROL</h1>
        </div>
        <div className="system-status">
          <div className="status-dot"></div>
          <span>SYSTEM ONLINE ({backendStatus.toUpperCase()})</span>
        </div>
      </header>

      {/* Main Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Left main panel */}
        <div className="main-panel">
          <div className="control-hub">
            <div className="tab-selector">
              <button 
                className={`tab-btn ${activeTab === 'webcam' ? 'active' : ''}`}
                onClick={() => { setActiveTab('webcam'); stopWebcamStream(); }}
              >
                LIVE CAMERA SCANNER
              </button>
              <button 
                className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
                onClick={() => { setActiveTab('upload'); stopWebcamStream(); }}
              >
                DRONE VIDEO ANALYSIS
              </button>
            </div>
            
            {activeTab === 'webcam' && (
              <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                <button 
                  className={`btn ${isCameraOn ? 'btn-danger' : ''}`}
                  onClick={() => setIsCameraOn(!isCameraOn)}
                >
                  {isCameraOn ? 'DEACTIVATE OPTICS' : 'ENGAGE LOCAL WEBCAM'}
                </button>
                {cameraError && <span style={{ color: 'var(--accent-red)', fontSize: '0.85rem' }}>{cameraError}</span>}
              </div>
            )}

            {activeTab === 'upload' && processedVideoUrl && (
              <button className="btn" onClick={resetUploadState}>
                ANALYZE NEW FOOTAGE
              </button>
            )}
          </div>

          <div className="viewport-card">
            {activeTab === 'webcam' ? (
              // Webcam Viewport
              isCameraOn ? (
                <div className="webcam-container">
                  {/* Native webcam stream preview */}
                  <video ref={videoRef} className="live-feed" playsInline muted></video>
                  {/* Transparent overlay canvas for dynamic client-side boxes */}
                  <canvas ref={overlayCanvasRef} style={{ pointerEvents: 'none', zIndex: 5 }}></canvas>
                  {/* Off-screen utility canvas for frame extraction */}
                  <canvas ref={canvasRef} style={{ display: 'none' }}></canvas>
                  
                  {/* HUD Text Overlay */}
                  <div className="hud-overlay">
                    <div className="hud-row">
                      <span>STREAM:</span>
                      <span style={{ color: '#fff' }}>MRO_VISION_CAM_01</span>
                    </div>
                    <div className="hud-row">
                      <span>LATENCY:</span>
                      <span style={{ color: '#fff' }}>{liveMetrics.latency} ms</span>
                    </div>
                    <div className="hud-row">
                      <span>THROUGHPUT:</span>
                      <span style={{ color: '#fff' }}>{liveMetrics.fps.toFixed(1)} FPS</span>
                    </div>
                    <div className="hud-row">
                      <span>SCAN INDEX:</span>
                      <span style={{ color: '#fff' }}>{liveMetrics.frameCount}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <svg className="upload-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" style={{ opacity: 0.3 }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
                  </svg>
                  <h3>Optic Sensor Disengaged</h3>
                  <p style={{ marginTop: '5px' }}>Click the "Engage Local Webcam" button above to start real-time crack inspection.</p>
                </div>
              )
            ) : (
              // Drone Video Upload Viewport
              processedVideoUrl || processing ? (
                <div className="processed-video-container">
                  <video 
                    ref={videoPlayerRef}
                    src={processedVideoUrl ? processedVideoUrl : undefined} 
                    className="video-player" 
                    controls
                    playsInline
                  ></video>
                  <div className="video-controls-bar">
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Source ID: {taskId?.slice(0, 8)}... {processing ? "(Processing live via HLS)" : "(Compiled with AVC1/H.264)"}
                    </span>
                    {processedVideoUrl && (
                      <a href={`${processedVideoUrl}/download`} download className="btn" style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
                        DOWNLOAD OUTPUT CLIP
                      </a>
                    )}
                  </div>
                </div>
              ) : uploading ? (
                <div className="processing-container">
                  <div className="status-text" style={{ color: 'var(--accent-blue)' }}>UPLOADING INSPECTION TAPE...</div>
                  <div className="progress-bar-container">
                    <div className="progress-bar" style={{ width: '100%', background: 'var(--accent-blue)', animation: 'pulse 1s infinite' }}></div>
                  </div>
                </div>
              ) : (
                <div 
                  className={`dropzone ${dragActive ? 'drag-active' : ''}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                >
                  <input 
                    ref={fileInputRef} 
                    type="file" 
                    accept="video/*" 
                    onChange={handleFileChange} 
                  />
                  <svg className="upload-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
                  </svg>
                  {selectedFile ? (
                    <div style={{ textAlign: 'center' }}>
                      <h3 style={{ color: 'var(--accent-green)' }}>{selectedFile.name}</h3>
                      <p style={{ marginTop: '10px' }}>Click 'INITIALIZE SCAN' button below to start processing.</p>
                      <button 
                        className="btn" 
                        style={{ marginTop: '20px' }} 
                        onClick={(e) => { e.stopPropagation(); handleUploadSubmit(); }}
                      >
                        INITIALIZE SCAN
                      </button>
                    </div>
                  ) : (
                    <>
                      <h3>Drag & Drop Drone Footage Here</h3>
                      <p>or click to browse local folders</p>
                    </>
                  )}
                  {uploadError && (
                    <p style={{ color: 'var(--accent-red)', marginTop: '15px', fontWeight: 'bold' }}>
                      {uploadError}
                    </p>
                  )}
                </div>
              )
            )}
          </div>
        </div>

        {/* Right Sidebar - Analytics Panel */}
        <div className="side-panel">
          <div className="telemetry-header">
            <span>ANOMALY TELEMETRY</span>
            {defectCount > 0 && <span style={{ color: 'var(--accent-red)', animation: 'pulse 1.5s infinite' }}>▲ ALERTS LOGGED</span>}
          </div>

          <div className="telemetry-summary">
            <div className="metric-card">
              <div className={`metric-val ${defectCount > 0 ? 'alert' : 'ok'}`}>{defectCount}</div>
              <div className="metric-lbl">TOTAL ALERTS</div>
            </div>
            <div className="metric-card">
              <div className="metric-val" style={{ color: 'var(--accent-blue)' }}>
                {activeTab === 'webcam' ? liveMetrics.fps.toFixed(1) : (processedVideoUrl ? processedVideoFps : 0)}
              </div>
              <div className="metric-lbl">FPS SPEED</div>
            </div>
          </div>

          {/* Sidebar Tabs for Logs vs SVG Charts */}
          <div className="sidebar-tabs">
            <button 
              className={`sidebar-tab-btn ${sidebarTab === 'logs' ? 'active' : ''}`}
              onClick={() => setSidebarTab('logs')}
            >
              ALERTS LOG
            </button>
            <button 
              className={`sidebar-tab-btn ${sidebarTab === 'charts' ? 'active' : ''}`}
              onClick={() => setSidebarTab('charts')}
            >
              ANALYTICS CHARTS
            </button>
          </div>

          {sidebarTab === 'charts' ? (
            <div className="charts-container" style={{ display: 'flex', flexDirection: 'column', gap: '15px', overflowY: 'auto', flex: 1 }}>
              <DefectBarChart counts={getDefectCounts()} />
              <SpatialLineChart data={getSpatialData()} />
            </div>
          ) : (
            activeTab === 'webcam' ? (
              // Live logs view
              <div className="logs-list">
                {liveLog.length === 0 ? (
                  <div className="log-empty">
                    <svg className="empty-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                    </svg>
                    <span>No defect detected. Structure appears sound.</span>
                  </div>
                ) : (
                  liveLog.map((log) => (
                    <div key={log.id} className={`log-item ${log.class}`}>
                      <div className="log-row-top">
                        <span className={`defect-badge ${log.class}`}>{log.class}</span>
                        <span className="log-confidence">{(log.confidence * 100).toFixed(0)}% CONF</span>
                      </div>
                      <div className="log-meta">
                        <span>Marker: {log.position} m</span>
                        <span>{log.timestamp}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            ) : (
              // Processed video alerts view
              <div className="logs-list">
                {videoAlerts.length === 0 ? (
                  <div className="log-empty">
                    <svg className="empty-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    {processedVideoUrl ? (
                      <span>Scan complete: No structural anomalies identified.</span>
                    ) : (
                      <span>Awaiting drone video analysis stream upload...</span>
                    )}
                  </div>
                ) : (
                  <>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '5px', textAlign: 'center' }}>
                      💡 Tip: Click on any alert to jump directly to that frame in the video!
                    </p>
                    {videoAlerts.map((alert, index) => {
                      const cls = alert.defect_metadata.detected_class;
                      const conf = alert.defect_metadata.confidence_score;
                      const pos = alert.payload_telemetry.estimated_tunnel_position_m;
                      return (
                        <div 
                          key={index} 
                          className={`log-item ${cls}`} 
                          onClick={() => handleLogClick(alert)}
                        >
                          <div className="log-row-top">
                            <span className={`defect-badge ${cls}`}>{cls}</span>
                            <span className="log-confidence">{(conf * 100).toFixed(0)}% CONF</span>
                          </div>
                          <div className="log-meta">
                            <span>Marker: {pos} m</span>
                            <span>Frame: {alert.frame_index}</span>
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
