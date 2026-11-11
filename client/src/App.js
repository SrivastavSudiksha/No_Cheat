/**
 * No_Cheat – Candidate Portal
 * Clean light theme • Black / grey accents
 * Camera + WebSocket streaming to detection service
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';

const DETECTION_WS = process.env.REACT_APP_DETECTION_WS || 'ws://localhost:8000/ws/stream';
const TOKEN_URL = process.env.REACT_APP_TOKEN_URL || 'http://localhost:8000/auth/token';
const FPS = 3;

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const seqRef = useRef(0);
  const intervalsRef = useRef([]);

  const [status, setStatus] = useState('idle');
  const [token, setToken] = useState('');
  const [sessionId, setSessionId] = useState('demo-session-001');
  const [events, setEvents] = useState([]);
  const [faceInfo, setFaceInfo] = useState({});
  const [cameraOn, setCameraOn] = useState(false);

  const fetchToken = async () => {
    const res = await fetch(TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, candidate_id: 'cand-001' }),
    });
    if (!res.ok) throw new Error('Token request failed');
    const data = await res.json();
    setToken(data.access_token);
    return data.access_token;
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
      setStatus('camera_ready');
    } catch (err) {
      console.error(err);
      setStatus('camera_error');
    }
  };

  const stopStreaming = () => {
    intervalsRef.current.forEach(clearInterval);
    intervalsRef.current = [];
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  const startSendingFrames = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');

    const frameInterval = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        clearInterval(frameInterval);
        return;
      }
      ctx.drawImage(video, 0, 0, 640, 480);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
      const base64 = dataUrl.split(',')[1];
      seqRef.current += 1;
      wsRef.current.send(
        JSON.stringify({
          type: 'frame',
          seq: seqRef.current,
          image: base64,
        })
      );
    }, 1000 / FPS);

    const hbInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 5000);

    intervalsRef.current = [frameInterval, hbInterval];
  }, []);

  const connectWs = useCallback(async () => {
    try {
      let tkn = token;
      if (!tkn) tkn = await fetchToken();

      stopStreaming();

      const ws = new WebSocket(DETECTION_WS);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'auth', token: tkn }));
        setStatus('connected');
      };

      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data);
        if (data.type === 'event') {
          setEvents((prev) => [data.event, ...prev].slice(0, 30));
        } else if (data.type === 'status') {
          setFaceInfo(data);
        } else if (data.type === 'auth_ok') {
          setStatus('streaming');
          startSendingFrames();
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        stopStreaming();
      };

      ws.onerror = () => setStatus('ws_error');
    } catch (err) {
      console.error(err);
      setStatus('ws_error');
    }
  }, [token, sessionId, startSendingFrames]);

  // Browser events → send to detection service
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ type: 'browser_event', event: 'TAB_HIDDEN' })
        );
      }
    };
    const onFullscreen = () => {
      if (!document.fullscreenElement && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({ type: 'browser_event', event: 'FULLSCREEN_EXIT' })
        );
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    document.addEventListener('fullscreenchange', onFullscreen);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      document.removeEventListener('fullscreenchange', onFullscreen);
      stopStreaming();
    };
  }, []);

  const enterFullscreen = () => {
    document.documentElement.requestFullscreen?.();
  };

  const statusLabel = {
    idle: 'Idle',
    camera_ready: 'Camera Ready',
    connected: 'Connected',
    streaming: 'Streaming',
    disconnected: 'Disconnected',
    camera_error: 'Camera Error',
    ws_error: 'Connection Error',
  }[status] || status;

  const statusClass = {
    idle: '',
    camera_ready: 'ready',
    connected: 'connected',
    streaming: 'streaming',
    disconnected: 'disconnected',
    camera_error: 'error',
    ws_error: 'error',
  }[status] || '';

  const severityClass = (sev) => {
    if (sev >= 0.8) return 'high';
    if (sev >= 0.5) return 'med';
    return '';
  };

  return (
    <>
      {/* Top bar – inspired by Max Healthcare style */}
      <div className="top-bar">
        <span>Secure exam proctoring • Real-time monitoring active</span>
        <span style={{ display: 'flex', gap: 20 }}>
          <a href="#support">Support</a>
          <a href="#docs">Documentation</a>
        </span>
      </div>

      {/* Main navbar */}
      <nav className="navbar">
        <div className="nav-left">
          <a href="/" className="logo">
            <div className="logo-mark">NC</div>
            <div className="logo-text">
              No_Cheat <span>· Candidate</span>
            </div>
          </a>
          <ul className="nav-links">
            <li><a href="#session" className="active">Exam Session</a></li>
            <li><a href="#events">Events</a></li>
            <li><a href="#help">Help</a></li>
          </ul>
        </div>
        <div className="nav-right">
          <button className="btn btn-outline btn-sm" onClick={enterFullscreen}>
            Fullscreen
          </button>
          <button
            className="btn btn-black btn-sm"
            onClick={connectWs}
            disabled={status === 'streaming' || !cameraOn}
          >
            {status === 'streaming' ? 'Live' : 'Start Proctoring'}
          </button>
        </div>
      </nav>

      <main className="page">
        <div className="page-header">
          <h1>Exam Session</h1>
          <p>Keep your face visible and look at the screen. Suspicious activity is logged automatically.</p>
        </div>

        <div className="status-row">
          <div className={`status-badge ${statusClass}`}>
            <span className="status-dot" />
            {statusLabel}
          </div>
          {status === 'streaming' && (
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Frames are being sent at {FPS} FPS
            </span>
          )}
        </div>

        <div className="main-grid">
          {/* Left: Video + controls */}
          <div>
            <div className="card">
              <div className="card-header">
                <h3>Webcam Feed</h3>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  640 × 480
                </span>
              </div>
              <div className="card-body">
                <div className="video-wrap">
                  <video
                    ref={videoRef}
                    muted
                    playsInline
                    style={{ background: '#0f172a' }}
                  />
                  <canvas
                    ref={canvasRef}
                    width={640}
                    height={480}
                    style={{ display: 'none' }}
                  />
                  {cameraOn && (
                    <div className="video-overlay">
                      <span>{status === 'streaming' ? '● Live' : 'Camera on'}</span>
                      <span>Session: {sessionId}</span>
                    </div>
                  )}
                </div>

                <div className="metrics">
                  <div className="metric">
                    <div className="metric-label">Faces</div>
                    <div className={`metric-value ${faceInfo.face_count > 1 ? 'danger' : ''}`}>
                      {faceInfo.face_count ?? '—'}
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric-label">Looking away</div>
                    <div className={`metric-value ${faceInfo.looking_away ? 'warn' : ''}`}>
                      {faceInfo.looking_away === undefined
                        ? '—'
                        : faceInfo.looking_away
                        ? 'Yes'
                        : 'No'}
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric-label">Yaw / Pitch</div>
                    <div className="metric-value" style={{ fontSize: 15 }}>
                      {faceInfo.yaw !== undefined
                        ? `${faceInfo.yaw}° / ${faceInfo.pitch}°`
                        : '—'}
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric-label">Total absence</div>
                    <div className={`metric-value ${faceInfo.total_absence_s > 10 ? 'warn' : ''}`}>
                      {faceInfo.total_absence_s !== undefined
                        ? `${faceInfo.total_absence_s}s`
                        : '—'}
                    </div>
                  </div>
                </div>

                <div className="controls">
                  <button
                    className="btn btn-black"
                    onClick={startCamera}
                    disabled={cameraOn}
                  >
                    {cameraOn ? 'Camera Active' : '1. Start Camera'}
                  </button>
                  <button
                    className="btn btn-black"
                    onClick={connectWs}
                    disabled={!cameraOn || status === 'streaming'}
                  >
                    2. Connect & Stream
                  </button>
                  <button className="btn btn-outline" onClick={enterFullscreen}>
                    Enter Fullscreen
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right: Session + Events */}
          <div>
            <div className="session-box">
              <label>Session ID</label>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                disabled={status === 'streaming'}
              />
            </div>

            <div className="card">
              <div className="card-header">
                <h3>Recent Events</h3>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {events.length} logged
                </span>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                {events.length === 0 ? (
                  <div className="empty-state">
                    No events yet.<br />
                    Start streaming to begin monitoring.
                  </div>
                ) : (
                  <ul className="events-list">
                    {events.map((e) => (
                      <li key={e.event_id} className="event-item">
                        <div className="event-type">
                          {e.type.replace(/_/g, ' ')}
                          <span className={`sev ${severityClass(e.severity)}`}>
                            sev {e.severity}
                          </span>
                        </div>
                        <div className="event-meta">
                          {e.duration_ms ? `${e.duration_ms} ms · ` : ''}
                          {e.server_ts
                            ? new Date(e.server_ts).toLocaleTimeString()
                            : ''}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>

        <footer className="footer">
          <span>No_Cheat · Exam proctoring system</span>
          <span>
            <a href="https://github.com/SrivastavSudiksha/No_Cheat" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </span>
        </footer>
      </main>
    </>
  );
}

export default App;
