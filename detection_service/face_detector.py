"""
Face count + FaceMesh landmarks + iris centers.
Uses MediaPipe only – no trained model needed for Phase 1.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, Optional, Tuple, List


class FaceDetector:
    def __init__(self, min_detection_confidence: float = 0.6):
        self.face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # full-range model
            min_detection_confidence=min_detection_confidence
        )
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=3,
            refine_landmarks=True,          # required for iris
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )

    def detect(self, frame_bgr: np.ndarray) -> Dict:
        """
        Returns dict with:
          - face_count
          - has_face
          - landmarks (list of MediaPipe landmarks of primary face)
          - bbox (x, y, w, h) of largest face
          - iris_landmarks {"left": (x,y), "right": (x,y)}
        """
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Lightweight face count
        det_results = self.face_detection.process(frame_rgb)
        face_count = 0
        largest_bbox = None
        max_area = 0

        if det_results.detections:
            face_count = len(det_results.detections)
            for det in det_results.detections:
                bbox = det.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                bw = int(bbox.width * w)
                bh = int(bbox.height * h)
                area = bw * bh
                if area > max_area:
                    max_area = area
                    largest_bbox = (x, y, bw, bh)

        landmarks = None
        iris_landmarks = None

        if face_count >= 1:
            mesh_results = self.face_mesh.process(frame_rgb)
            if mesh_results.multi_face_landmarks:
                face_lms = mesh_results.multi_face_landmarks[0]
                landmarks = face_lms.landmark

                # Iris centers (refined landmarks)
                left_iris = landmarks[468]
                right_iris = landmarks[473]
                iris_landmarks = {
                    "left": (left_iris.x * w, left_iris.y * h),
                    "right": (right_iris.x * w, right_iris.y * h)
                }

        return {
            "face_count": face_count,
            "has_face": face_count >= 1,
            "landmarks": landmarks,
            "bbox": largest_bbox,
            "iris_landmarks": iris_landmarks
        }

    def close(self):
        self.face_detection.close()
        self.face_mesh.close()
