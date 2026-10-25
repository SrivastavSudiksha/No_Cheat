"""
Geometric head-pose (solvePnP) + iris ratio gaze estimation.
No trained model required for MVP.
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple


class GazeEstimator:
    # Approximate 3D model points (mm)
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye left corner
        (225.0, 170.0, -135.0),      # Right eye right corner
        (-150.0, -150.0, -125.0),    # Left mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ], dtype=np.float64)

    # Corresponding MediaPipe FaceMesh indices
    LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

    def __init__(self, image_size: Tuple[int, int] = (640, 480)):
        self.image_size = image_size
        focal_length = image_size[0]
        center = (image_size[0] / 2, image_size[1] / 2)
        self.camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        self.dist_coeffs = np.zeros((4, 1))

    def estimate(self, landmarks, iris_landmarks: Optional[Dict], frame_shape) -> Dict:
        h, w = frame_shape[:2]

        if landmarks is None or len(landmarks) < 300:
            return self._empty()

        # ----- Head pose -----
        image_points = []
        for idx in self.LANDMARK_IDS:
            lm = landmarks[idx]
            image_points.append((lm.x * w, lm.y * h))
        image_points = np.array(image_points, dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            self.MODEL_POINTS,
            image_points,
            self.camera_matrix,
            self.dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return self._empty()

        rmat, _ = cv2.Rodrigues(rvec)
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        pitch, yaw, roll = float(angles[0]), float(angles[1]), float(angles[2])

        # ----- Iris ratio (horizontal gaze) -----
        gaze_x, gaze_y = 0.0, 0.0
        if iris_landmarks:
            left_iris = iris_landmarks["left"]
            right_iris = iris_landmarks["right"]

            left_outer = landmarks[33]
            left_inner = landmarks[133]
            right_outer = landmarks[263]
            right_inner = landmarks[362]

            def ratio(iris, outer, inner):
                eye_w = abs(inner.x - outer.x) * w
                if eye_w < 1:
                    return 0.0
                offset = iris[0] - (outer.x * w)
                return (offset / eye_w) * 2 - 1

            left_r = ratio(left_iris, left_outer, left_inner)
            right_r = ratio(right_iris, right_outer, right_inner)
            gaze_x = (left_r + right_r) / 2.0
            gaze_y = np.clip(pitch / 30.0, -1.0, 1.0)

        looking_away = abs(yaw) > 25 or abs(pitch) > 20 or abs(gaze_x) > 0.55

        return {
            "yaw": yaw,
            "pitch": pitch,
            "roll": roll,
            "gaze_x": float(gaze_x),
            "gaze_y": float(gaze_y),
            "looking_away": looking_away,
            "confidence": 0.85 if success else 0.3
        }

    def _empty(self):
        return {
            "yaw": 0.0, "pitch": 0.0, "roll": 0.0,
            "gaze_x": 0.0, "gaze_y": 0.0,
            "looking_away": False,
            "confidence": 0.0
        }
