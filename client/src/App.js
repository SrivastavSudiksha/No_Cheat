/**
 * Candidate client – Phase 4 skeleton
 * - Camera capture
 * - WebSocket to detection service
 * - Fullscreen + tab visibility events
 * - Heartbeat
 * - Sequence numbered frames
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';

const DETECTION_WS = process.env.REACT_APP_DETECTION_WS || 'ws://localhost:8000/ws/stream';
const FPS = 3;

function App() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const seqRef = useRef(0);
  const [status, setStatus] = useState('idle');
  const [token, setToken] = useState('');
  const [sessionId, setSessionId] = useState('demo-session-001');
  const [events, setEvents] = useState([]);
  const [faceInfo, setFaceInfo] = useState({});

  // Get token (in real app Spring Boot issues it)
  const fetchToken = async () => {
    const res = await fetch('http://localhost:8000/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, candidate_id: 'cand-001' })
    });
    const data = await res.json();
    setToken(data.access_token);
    return data.access_token;
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setStatus('camera_ready');
    } catch (err) {
      console.error(err);
      setStatus('camera_error');
    }
  };

  const connectWs = useCallback(async () => {
    let tkn = token;
    if (!tkn) tkn = await fetchToken();

    const ws = new WebSocket(DETECTION_WS);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token: tkn }));
      setStatus('connected');
    };

    ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.type === 'event') {
        setEvents(prev => [data.event, ...prev].slice(0, 20));
      } else if (data.type === 'status') {
        setFaceInfo(data);
      } else if (data.type === 'auth_ok') {
        setStatus('streaming');
        startSendingFrames();
      }
    };

    ws.onclose = () => setStatus('disconnected');
    ws.onerror = () => setStatus('ws_error');
  }, [token, sessionId]);

  const startSendingFrames = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    const interval = setInterval(() => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        clearInterval(interval);
        return;
      }
      ctx.drawImage(video, 0, 0, 640, 480);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
      const base64 = dataUrl.split(',')[1];
      seqRef.current += 1;
      wsRef.current.send(JSON.stringify({
        type: 'frame',
        seq: seqRef.current,
        image: base64
      }));
    }, 1000 / FPS);

    // Heartbeat
    const hb = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 5000);

    return () => {
      clearInterval(interval);
      clearInterval(hb);
    };
  };

  // Browser events
  useEffect(() => {
    const onVisibility = () => {
      if (document.hidden && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'browser_event',
          event: 'TAB_HIDDEN'
        }));
      }
    };
    const onFullscreen = () => {
      if (!document.fullscreenElement && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'browser_event',
          event: 'FULLSCREEN_EXIT'
        }));
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    document.addEventListener('fullscreenchange', onFullscreen);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      document.removeEventListener('fullscreenchange', onFullscreen);
    };
  }, []);

  const enterFullscreen = () => {
    document.documentElement.requestFullscreen?.();
  };

  return (
    <div style={{ fontFamily: 'system-ui', padding: 20, maxWidth: 900, margin: '0 auto' }}>
      <h1>No_Cheat – Candidate</h1>
      <p>Status: <strong>{status}</strong></p>

      <div style={{ display: 'flex', gap: 20 }}>
        <div>
          <video ref={videoRef} width={320} height={240} muted playsInline style={{ background: '#111' }} />
          <canvas ref={canvasRef} width={640} height={480} style={{ display: 'none' }} />
        </div>
        <div>
          <p>Face count: {faceInfo.face_count ?? '-'}</p>
          <p>Yaw: {faceInfo.yaw ?? '-'} | Pitch: {faceInfo.pitch ?? '-'}</p>
          <p>Looking away: {String(faceInfo.looking_away)}</p>
          <p>Total absence: {faceInfo.total_absence_s ?? 0}s</p>
        </div>
      </div>

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button onClick={startCamera}>1. Start Camera</button>
        <button onClick={connectWs} disabled={status === 'streaming'}>2. Connect & Stream</button>
        <button onClick={enterFullscreen}>Enter Fullscreen</button>
      </div>

      <h3 style={{ marginTop: 24 }}>Recent Events</h3>
      <ul style={{ fontSize: 13 }}>
        {events.map(e => (
          <li key={e.event_id}>
            [{e.type}] sev={e.severity} {e.duration_ms ? `(${e.duration_ms}ms)` : ''}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
