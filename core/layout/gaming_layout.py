import cv2
import numpy as np
from typing import Optional, Dict

class GamingLayoutDetector:
    def __init__(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
            self.face_cascade = None

    def detect_streamer_facecam(
        self,
        video_path: str,
        sample_count: int = 15,
        layout_preset: str = "auto"
    ) -> Optional[Dict[str, int]]:
        """
        Scan frames to locate the persistent streamer facecam box.
        Filters out in-game cinematic faces by identifying the stationary cluster
        located in typical streamer overlay zones (left/right/corners).
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Fast preset overrides if requested
            if layout_preset in ["left", "facecam_left", "speed"]:
                cap.release()
                return {
                    "x": 0,
                    "y": int(orig_h * 0.38),
                    "w": int(orig_w * 0.23),
                    "h": int(orig_h * 0.28),
                    "orig_w": orig_w,
                    "orig_h": orig_h
                }
            elif layout_preset in ["right", "facecam_right"]:
                cap.release()
                return {
                    "x": int(orig_w * 0.74),
                    "y": int(orig_h * 0.65),
                    "w": int(orig_w * 0.26),
                    "h": int(orig_h * 0.35),
                    "orig_w": orig_w,
                    "orig_h": orig_h
                }

            if self.face_cascade is None or self.face_cascade.empty() or total_frames <= 0:
                cap.release()
                return None

            detected_boxes = []
            step = max(1, total_frames // sample_count)

            for i in range(sample_count):
                frame_idx = i * step
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # Lower minSize to catch small webcam overlays
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(20, 20))

                for (x, y, w, h) in faces:
                    detected_boxes.append((x, y, w, h))

            cap.release()

            if not detected_boxes:
                return None

            # Filter 1: Streamer facecams are in boundary/edge zones (NOT dead center)
            # Center of screen is where in-game cinematics, trailer faces, and game characters appear
            edge_boxes = []
            for (x, y, w, h) in detected_boxes:
                cx = x + w / 2
                cy = y + h / 2
                # Check if near edges (left 35%, right 35%, top 25%, bottom 25%)
                if cx < 0.35 * orig_w or cx > 0.65 * orig_w or cy < 0.25 * orig_h or cy > 0.75 * orig_h:
                    edge_boxes.append((x, y, w, h))

            # Prefer edge boxes if any found; fallback to all if none
            candidate_boxes = edge_boxes if edge_boxes else detected_boxes

            # Filter 2: Find the most STATIONARY cluster (streamer webcam stays in same place across cuts)
            best_cluster = []
            tolerance = max(30, int(orig_w * 0.08))
            for b in candidate_boxes:
                neighbors = [o for o in candidate_boxes if abs(o[0] - b[0]) < tolerance and abs(o[1] - b[1]) < tolerance]
                if len(neighbors) > len(best_cluster):
                    best_cluster = neighbors

            if not best_cluster:
                best_cluster = candidate_boxes

            cluster_arr = np.array(best_cluster)
            med_x = int(np.median(cluster_arr[:, 0]))
            med_y = int(np.median(cluster_arr[:, 1]))
            med_w = int(np.median(cluster_arr[:, 2]))
            med_h = int(np.median(cluster_arr[:, 3]))

            # Expand to capture the webcam frame/overlay
            # If face is near left border (like IShowSpeed)
            if med_x < 0.25 * orig_w:
                x1 = 0
                w_box = max(int(orig_w * 0.23), med_w * 3)
                y1 = max(0, int(med_y - med_h * 1.0))
                h_box = max(int(orig_h * 0.28), med_h * 3)
            # If face is near right border
            elif med_x > 0.65 * orig_w:
                w_box = max(int(orig_w * 0.25), med_w * 3)
                x1 = max(0, orig_w - w_box)
                y1 = max(0, int(med_y - med_h * 1.0))
                h_box = max(int(orig_h * 0.30), med_h * 3)
            else:
                pad_w = int(med_w * 1.2)
                pad_h = int(med_h * 1.2)
                x1 = max(0, med_x - pad_w)
                y1 = max(0, med_y - pad_h)
                w_box = min(orig_w - x1, med_w + 2 * pad_w)
                h_box = min(orig_h - y1, med_h + 2 * pad_h)

            return {
                "x": int(x1),
                "y": int(y1),
                "w": int(w_box),
                "h": int(h_box),
                "orig_w": orig_w,
                "orig_h": orig_h
            }

        except Exception as e:
            print(f"[GamingLayoutDetector] Facecam detection warning: {e}")
            return None
