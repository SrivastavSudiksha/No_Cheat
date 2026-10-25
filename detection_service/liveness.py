"""
Liveness challenges (Phase 6 skeleton).
Random surprise challenges + blink detection.
"""

import random
import time
from typing import Dict, Optional
import mediapipe as mp
import numpy as np


class LivenessChecker:
    CHALLENGES = [
        "blink_twice",
        "turn_head_left",
        "turn_head_right",
        "look_up",
        "say_digit"           # audio later
    ]

    def __init__(self):
        self.pending_challenge: Optional[str] = None
        self.challenge_issued_at: Optional[float] = None
        self.challenge_timeout = 8.0  # seconds

    def maybe_issue_challenge(self, force: bool = False) -> Optional[str]:
        """Call periodically. Returns challenge name if issued."""
        if self.pending_challenge:
            return None
        if force or random.random() < 0.02:  # ~2% chance per call
            self.pending_challenge = random.choice(self.CHALLENGES)
            self.challenge_issued_at = time.time()
            return self.pending_challenge
        return None

    def check_timeout(self) -> bool:
        if self.pending_challenge and self.challenge_issued_at:
            if time.time() - self.challenge_issued_at > self.challenge_timeout:
                self.pending_challenge = None
                return True  # failed
        return False

    def verify_blink(self, landmarks) -> bool:
        """Simple eye aspect ratio based blink (placeholder)."""
        # Real implementation uses EAR on landmarks 159,145 etc.
        return False  # TODO

    def clear_challenge(self):
        self.pending_challenge = None
        self.challenge_issued_at = None
