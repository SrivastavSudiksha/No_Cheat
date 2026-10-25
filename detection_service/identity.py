"""
Identity verification (Phase 6 skeleton).
Compare live face embedding against institute-provided enrollment photo.
Uses face_recognition or InsightFace in production.
"""

from typing import Optional, Tuple
import numpy as np


class IdentityVerifier:
    def __init__(self):
        # In production: load InsightFace or face_recognition model
        self.enrollment_embedding: Optional[np.ndarray] = None
        self.last_verify_ts = 0.0
        self.reverify_interval = 300  # 5 min

    def set_enrollment(self, embedding: np.ndarray):
        """Called once at exam start with institute photo embedding."""
        self.enrollment_embedding = embedding

    def should_reverify(self) -> bool:
        return (time.time() - self.last_verify_ts) > self.reverify_interval

    def verify(self, live_embedding: np.ndarray, threshold: float = 0.6) -> Tuple[bool, float]:
        """
        Returns (match: bool, similarity: float)
        """
        if self.enrollment_embedding is None:
            return False, 0.0
        # Cosine similarity placeholder
        sim = float(np.dot(self.enrollment_embedding, live_embedding) /
                    (np.linalg.norm(self.enrollment_embedding) * np.linalg.norm(live_embedding) + 1e-8))
        self.last_verify_ts = time.time()
        return sim >= threshold, sim


import time  # for should_reverify
