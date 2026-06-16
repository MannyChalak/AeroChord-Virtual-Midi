import cv2
import logging
import numpy as np
from typing import Tuple, Optional


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(name)s - %(message)s')
logger = logging.getLogger("Vision")

class WebcamHandler:
    def __init__(self, camera_index: int = 0) -> None:
        """
        Initialize the webcam.
        :param camera_index: Windows camera index (usually 0 for the default camera)
        """
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            logger.error(f"Cannot open webcam with index {self.camera_index}. Please check connection.")
        else:
            logger.info("Webcam initialized successfully.")

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture a single frame from the camera.
        :return: A tuple containing the success status (bool) and the image frame (ndarray)
        """
        if not self.cap.isOpened():
            return False, None
            
        ret, frame = self.cap.read()
        
        if not ret:
            logger.warning("Failed to grab frame from webcam. Camera might be disconnected.")
            return False, None
            
        frame = cv2.flip(frame, 1)
        return True, frame

    def release(self) -> None:
        """
        Release camera resources to prevent memory leaks or hanging processes in Windows.
        """
        if self.cap.isOpened():
            self.cap.release()
            logger.info("Webcam released safely.")