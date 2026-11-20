import cv2
import numpy as np
from typing import Optional, Dict

class PodcastLayoutDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def detect_podcast_speakers(self, video_path: str, sample_count: int = 12) -> Optional[Dict]:
        """
        Scans frames of a 16:9 interview/podcast video to locate two main speakers (Host on Left, Guest on Right).
        Returns bounding crop definitions for Speaker 1 (Top) and Speaker 2 (Bottom) for 9:16 split screen.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return None

        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        mid_x = orig_w // 2

        left_faces = []
        right_faces = []
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
                center_x = x + w // 2
                if center_x < mid_x:
                    left_faces.append((x, y, w, h))
                else:
                    right_faces.append((x, y, w, h))

        cap.release()

        # Target crop aspect ratio for each speaker is 1080 : 960 (9 : 8)
        # So crop_w = crop_h * (9 / 8) or crop_h = crop_w * (8 / 9)
        # In a 16:9 video (e.g. 1920x1080), maximum height per speaker is orig_h.
        target_crop_h = orig_h
        target_crop_w = int(orig_h * (9 / 8))
        if target_crop_w > orig_w // 2:
            target_crop_w = orig_w // 2
            target_crop_h = int(target_crop_w * (8 / 9))

        def get_speaker_crop(faces_list, default_center_x):
            if faces_list:
                boxes = np.array(faces_list)
                med_x = int(np.median(boxes[:, 0]))
                med_y = int(np.median(boxes[:, 1]))
                med_w = int(np.median(boxes[:, 2]))
                med_h = int(np.median(boxes[:, 3]))
                cx = med_x + med_w // 2
                cy = med_y + med_h // 2
            else:
                cx = default_center_x
                cy = orig_h // 2

            # Compute crop box centered at (cx, cy)
            x1 = max(0, min(orig_w - target_crop_w, cx - target_crop_w // 2))
            y1 = max(0, min(orig_h - target_crop_h, cy - target_crop_h // 2))
            return {
                "x": int(x1),
                "y": int(y1),
                "w": int(target_crop_w),
                "h": int(target_crop_h)
            }

        # If both left and right speakers detected, or at least one
        if not left_faces and not right_faces:
            return None

        speaker_left = get_speaker_crop(left_faces, orig_w // 4)
        speaker_right = get_speaker_crop(right_faces, (3 * orig_w) // 4)

        return {
            "speaker_left": speaker_left,
            "speaker_right": speaker_right,
            "has_dual_speakers": bool(left_faces and right_faces),
            "orig_w": orig_w,
            "orig_h": orig_h
        }
