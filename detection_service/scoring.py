"""
Risk scoring engine (Phase 5 skeleton).
Weighted sum over rolling time window.
Final decision always human.
"""

from collections import deque
from typing import Dict, List
import time


class RiskScorer:
    # Configurable weights
    WEIGHTS = {
        "MULTIPLE_FACES": 0.90,
        "NO_FACE": 0.70,
        "ABSENCE_BUDGET_EXCEEDED": 0.95,
        "LOOKING_AWAY": 0.35,
        "PHONE": 0.80,
        "BOOK_NOTES": 0.75,
        "EARBUDS": 0.65,
        "IDENTITY_MISMATCH": 0.95,
        "LIVENESS_FAIL": 0.90,
        "FROZEN_FRAME": 0.70,
        "TAB_SWITCH": 0.40,
        "FULLSCREEN_EXIT": 0.45,
        "SECOND_VOICE": 0.55,
        "CONNECTION_GAP": 0.60,
    }

    def __init__(self, window_seconds: int = 300):
        self.window = window_seconds
        self.events: deque = deque()

    def add_event(self, event: dict):
        self.events.append({
            "ts": time.time(),
            "type": event["type"],
            "severity": event.get("severity", 0.5)
        })
        self._prune()

    def _prune(self):
        cutoff = time.time() - self.window
        while self.events and self.events[0]["ts"] < cutoff:
            self.events.popleft()

    def score(self) -> Dict:
        self._prune()
        total = 0.0
        breakdown = {}
        for e in self.events:
            w = self.WEIGHTS.get(e["type"], 0.3)
            contrib = w * e["severity"]
            total += contrib
            breakdown[e["type"]] = breakdown.get(e["type"], 0) + contrib

        # Cap at 1.0
        risk = min(1.0, total)
        level = "low"
        if risk >= 0.75:
            level = "critical"
        elif risk >= 0.45:
            level = "high"
        elif risk >= 0.25:
            level = "medium"

        return {
            "risk_score": round(risk, 3),
            "level": level,
            "breakdown": {k: round(v, 3) for k, v in breakdown.items()},
            "event_count": len(self.events)
        }
