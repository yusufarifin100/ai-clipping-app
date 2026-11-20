import cv2
import numpy as np
from typing import Optional, Dict

class TalkingHeadLayoutDetector:
    def __init__(self):
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception:
            self.face_cascade = None

    def detect_talking_head(self, video_path: str, sample_count: int = 12) -> Optional[Dict]:
        """
        Scans frames of a 16:9 solo creator / commentary / educational video to locate the speaker.
        Calculates a 9:16 portrait crop centered on the speaker's median horizontal position.
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            faces_detected = []
            if self.face_cascade and not self.face_cascade.empty() and total_frames > 0:
                step = max(1, total_frames // sample_count)
                for i in range(sample_count):
                    frame_idx = i * step
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        continue

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

                    for (x, y, w, h) in faces:
                        faces_detected.append((x, y, w, h))

            cap.release()

            crop_h = orig_h
            crop_w = int(orig_h * (9 / 16))
            if crop_w > orig_w:
                crop_w = orig_w
                crop_h = int(crop_w * (16 / 9))

            if not faces_detected:
                center_x = orig_w // 2
            else:
                boxes = np.array(faces_detected)
                centers_x = boxes[:, 0] + boxes[:, 2] / 2
                center_x = int(np.median(centers_x))

            x1 = max(0, min(orig_w - crop_w, center_x - crop_w // 2))
            y1 = max(0, (orig_h - crop_h) // 2)

            return {
                "x": int(x1),
                "y": int(y1),
                "w": int(crop_w),
                "h": int(crop_h),
                "face_detected": bool(faces_detected),
                "orig_w": orig_w,
                "orig_h": orig_h
            }
        except Exception as e:
            print(f"[TalkingHeadLayoutDetector] Warning: {e}")
            return None
