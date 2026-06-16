import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import logging
import numpy as np
import time
from typing import List, Tuple

logger = logging.getLogger("Tracker")

class HandTracker:
    def __init__(self, model_path: str = "hand_landmarker.task", max_hands: int = 2) -> None:
        """
        Initialize the modern MediaPipe Tasks API for Hand Tracking.
        
        :param model_path: Path to the downloaded .task model file
        :param max_hands: Maximum number of hands to detect
        """
        self.model_path = model_path
        
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO, # Optimized for consecutive frames
            num_hands=max_hands,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        try:
            self.detector = vision.HandLandmarker.create_from_options(options)
            logger.info("Modern MediaPipe Tasks HandTracker initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load model. Ensure '{model_path}' exists in the root folder. Error: {e}")
            raise e

    def process_frame(self, frame: np.ndarray) -> List[List[Tuple[float, float, float]]]:
        """
        Process the frame and extract raw X, Y, Z coordinates.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        timestamp_ms = int(time.time() * 1000)
        
        detection_result = self.detector.detect_for_video(mp_image, timestamp_ms)
        
        hands_landmarks: List[List[Tuple[float, float, float]]] = []
        
        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                landmarks_list = [(lm.x, lm.y, lm.z) for lm in hand_landmarks]
                hands_landmarks.append(landmarks_list)
                
        return hands_landmarks

    def release(self) -> None:
        """
        Close and release the MediaPipe model resources safely.
        """
        if hasattr(self, 'detector'):
            self.detector.close()
            logger.info("Hand Tracker resources released.")