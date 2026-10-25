"""
No_Cheat Detection Service – Phase 1 (Hardened)
- JWT token auth
- Sequence number integrity
- Frozen / loop frame detection
- No-face absence budget
- Looking-away continuous + will be extended with cumulative
- Event emission with server-side timestamp
- Single connection enforcement (basic)
"""

import asyncio
import base64
import hashlib
import json
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Optional

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
import aiofiles

from face_detector import FaceDetector
from gaze_estimator import GazeEstimator

# ---------- Config ----------
SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET_IN_PRODUCTION_32CHARS+")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 180
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "./evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Absence budget (seconds)
ABSENCE_BUDGET_SECONDS = 25
MAX_SINGLE_ABSENCE = 10

app = FastAPI(title="No_Cheat Detection Service", version="1.0.0-phase1")
security = HTTPBearer()

face_detector = FaceDetector()
gaze_estimator = GazeEstimator()

# In-memory (replace with Redis in production)
active_sessions: Dict[str, dict] = {}


# ---------- Auth ----------
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = time.time() + TOKEN_EXPIRE_MINUTES * 60
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("session_id") is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


class TokenRequest(BaseModel):
    session_id: str
    candidate_id: str


@app.post("/auth/token")
def get_token(req: TokenRequest):
    """Helper endpoint. In production Spring Boot issues the JWT."""
    token = create_access_token({
        "session_id": req.session_id,
        "candidate_id": req.candidate_id,
        "role": "candidate"
    })
    return {"access_token": token, "token_type": "bearer"}


# ---------- Event helper ----------
def make_event(session_id: str, event_type: str, severity: float,
               confidence: float = 0.0, duration_ms: int = 0,
               evidence_url: Optional[str] = None, extra: dict = None) -> dict:
    event = {
        "event_id": str(uuid.uuid4()),
        "session_id": session_id,
        "type": event_type,
        "severity": round(severity, 3),
        "confidence": round(confidence, 3),
        "server_ts": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "evidence_url": evidence_url,
    }
    if extra:
        event["extra"] = extra
    return event


async def save_evidence(session_id: str, frame: np.ndarray, prefix: str = "snap") -> str:
    """Save JPEG snapshot and return relative URL."""
    fname = f"{prefix}_{session_id}_{int(time.time()*1000)}.jpg"
    path = os.path.join(EVIDENCE_DIR, fname)
    cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return f"/evidence/{fname}"


# ---------- WebSocket ----------
@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    session_id = None
    last_seq = -1
    last_frame_hash = None
    consecutive_same = 0
    no_face_start: Optional[float] = None
    total_absence_seconds = 0.0
    look_away_start: Optional[float] = None
    last_heartbeat = time.time()

    try:
        # ---- Auth message ----
        auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        if auth_msg.get("type") != "auth":
            await websocket.close(code=4001)
            return

        token = auth_msg.get("token")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            session_id = payload["session_id"]
        except JWTError:
            await websocket.close(code=4003)
            return

        # Single connection enforcement (basic)
        if session_id in active_sessions:
            # Already connected → reject new one
            await websocket.send_json({"type": "error", "msg": "session_already_active"})
            await websocket.close(code=4009)
            return

        active_sessions[session_id] = {
            "connected_at": time.time(),
            "last_heartbeat": time.time(),
            "frame_count": 0,
            "total_absence": 0.0
        }

        await websocket.send_json({"type": "auth_ok", "session_id": session_id})

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "heartbeat":
                active_sessions[session_id]["last_heartbeat"] = time.time()
                last_heartbeat = time.time()
                await websocket.send_json({
                    "type": "heartbeat_ack",
                    "server_ts": datetime.now(timezone.utc).isoformat()
                })
                continue

            if msg_type != "frame":
                continue

            # ---- Sequence integrity ----
            seq = data.get("seq", -1)
            if seq <= last_seq:
                await websocket.send_json({"type": "error", "msg": "invalid_or_replayed_sequence"})
                continue
            last_seq = seq

            # ---- Decode frame ----
            try:
                img_bytes = base64.b64decode(data["image"])
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
            except Exception:
                continue

            # ---- Frozen / injected frame detection ----
            frame_hash = hashlib.md5(frame.tobytes()).hexdigest()
            if frame_hash == last_frame_hash:
                consecutive_same += 1
            else:
                consecutive_same = 0
            last_frame_hash = frame_hash

            if consecutive_same >= 8:  # ~2-3s at 3 FPS
                evidence = await save_evidence(session_id, frame, "frozen")
                event = make_event(
                    session_id, "FROZEN_FRAME", severity=0.75,
                    confidence=0.9, evidence_url=evidence,
                    extra={"consecutive_same": consecutive_same}
                )
                await websocket.send_json({"type": "event", "event": event})
                # TODO: also POST to Spring Boot

            # ---- Run detectors ----
            face_result = face_detector.detect(frame)
            gaze_result = gaze_estimator.estimate(
                face_result["landmarks"],
                face_result["iris_landmarks"],
                frame.shape
            )

            active_sessions[session_id]["frame_count"] += 1
            now = time.time()

            # ---- No-face with absence budget ----
            if not face_result["has_face"]:
                if no_face_start is None:
                    no_face_start = now
                duration = now - no_face_start
                total_absence_seconds += 0.33  # approximate per frame at ~3 FPS

                if duration > MAX_SINGLE_ABSENCE:
                    evidence = await save_evidence(session_id, frame, "noface")
                    event = make_event(
                        session_id, "NO_FACE", severity=0.85,
                        confidence=0.95, duration_ms=int(duration * 1000),
                        evidence_url=evidence,
                        extra={"total_absence_s": round(total_absence_seconds, 1)}
                    )
                    await websocket.send_json({"type": "event", "event": event})

                if total_absence_seconds > ABSENCE_BUDGET_SECONDS:
                    event = make_event(
                        session_id, "ABSENCE_BUDGET_EXCEEDED", severity=0.95,
                        confidence=1.0,
                        extra={"total_absence_s": round(total_absence_seconds, 1)}
                    )
                    await websocket.send_json({"type": "event", "event": event})
            else:
                no_face_start = None

            # ---- Multiple faces ----
            if face_result["face_count"] >= 2:
                evidence = await save_evidence(session_id, frame, "multiface")
                event = make_event(
                    session_id, "MULTIPLE_FACES", severity=0.95,
                    confidence=0.9, evidence_url=evidence,
                    extra={"count": face_result["face_count"]}
                )
                await websocket.send_json({"type": "event", "event": event})

            # ---- Looking away (continuous) ----
            if gaze_result["looking_away"] and face_result["has_face"]:
                if look_away_start is None:
                    look_away_start = now
                duration = now - look_away_start
                if duration > 3.0:
                    evidence = await save_evidence(session_id, frame, "lookaway")
                    event = make_event(
                        session_id, "LOOKING_AWAY",
                        severity=0.55,
                        confidence=gaze_result["confidence"],
                        duration_ms=int(duration * 1000),
                        evidence_url=evidence,
                        extra={
                            "yaw": round(gaze_result["yaw"], 1),
                            "pitch": round(gaze_result["pitch"], 1),
                            "gaze_x": round(gaze_result["gaze_x"], 3)
                        }
                    )
                    await websocket.send_json({"type": "event", "event": event})
            else:
                look_away_start = None

            # Lightweight status every 10 frames (for client debug UI)
            if active_sessions[session_id]["frame_count"] % 10 == 0:
                await websocket.send_json({
                    "type": "status",
                    "face_count": face_result["face_count"],
                    "yaw": round(gaze_result["yaw"], 1),
                    "pitch": round(gaze_result["pitch"], 1),
                    "looking_away": gaze_result["looking_away"],
                    "total_absence_s": round(total_absence_seconds, 1)
                })

    except asyncio.TimeoutError:
        await websocket.close(code=4008)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Error] {e}")
    finally:
        if session_id and session_id in active_sessions:
            del active_sessions[session_id]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.on_event("shutdown")
def shutdown_event():
    face_detector.close()
