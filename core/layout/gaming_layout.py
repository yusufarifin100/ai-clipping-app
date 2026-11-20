import cv2
import numpy as np
from typing import Optional, Dict

class GamingLayoutDetector:
    def __init__(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
            self.face_cascade = None

    def detect_streamer_facecam(self, video_path: str, sample_count: int = 10) -> Optional[Dict[str, int]]:
        """
        Scan frames to locate the persistent streamer facecam box.
        Returns dict with x, y, w, h relative to original video size, or None.
        """
        if self.face_cascade is None or self.face_cascade.empty():
            return None

        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                cap.release()
                return None

            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            detected_boxes = []
            step = max(1, total_frames // sample_count)

            for i in range(sample_count):
                frame_idx = i * step
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))

                for (x, y, w, h) in faces:
                    detected_boxes.append((x, y, w, h))

            cap.release()

            if not detected_boxes:
                return None

            # Cluster boxes to find stationary facecam
            boxes = np.array(detected_boxes)
            median_x = int(np.median(boxes[:, 0]))
            median_y = int(np.median(boxes[:, 1]))
            median_w = int(np.median(boxes[:, 2]))
            median_h = int(np.median(boxes[:, 3]))

            # Expand box by 50% to capture full head/webcam border
            pad_w = int(median_w * 0.5)
            pad_h = int(median_h * 0.6)

            x1 = max(0, median_x - pad_w)
            y1 = max(0, median_y - pad_h)
            x2 = min(orig_w, median_x + median_w + pad_w)
            y2 = min(orig_h, median_y + median_h + pad_h)

            return {
                "x": x1,
                "y": y1,
                "w": x2 - x1,
                "h": y2 - y1,
                "orig_w": orig_w,
                "orig_h": orig_h
            }
        except Exception as e:
            print(f"[GamingLayoutDetector] Facecam detection warning: {e}")
            return None
