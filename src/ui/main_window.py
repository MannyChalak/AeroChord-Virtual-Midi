import cv2
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                             QWidget, QComboBox, QCheckBox, QFrame)
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from .overlay import OverlayWidget

class VisionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    update_overlay_signal = pyqtSignal(list, set)

    def __init__(self, vision_handler, tracker, mapper, midi_out):
        super().__init__()
        self.vision_handler = vision_handler
        self.tracker = tracker
        self.mapper = mapper
        self.midi_out = midi_out
        self._run_flag = True

    def run(self):
        while self._run_flag:
            ret, frame = self.vision_handler.get_frame()
            if not ret: continue

            hands_landmarks = self.tracker.process_frame(frame)
            events = self.mapper.process_landmarks(hands_landmarks)
            
            for event in events:
                if "just_entered" in event and event["just_entered"]:
                    self.midi_out.send_note_on(event["note"], velocity=100)
                elif "just_left" in event and event["just_left"]:
                    self.midi_out.send_note_off(event["note"], velocity=0)
                if "cc_value" in event:
                    self.midi_out.send_cc(control=1, value=event["cc_value"])
            
            current_active_zones = {z.name for z in self.mapper.zones if z.is_active}
            self.update_overlay_signal.emit(self.mapper.zones, current_active_zones)
            self.change_pixmap_signal.emit(frame)

    def stop(self):
        self._run_flag = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self, vision_handler, tracker, mapper, midi_out):
        super().__init__()
        self.mapper = mapper 
        self.setWindowTitle("AeroChord - Live Performance")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #000000;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.video_container = QWidget()
        video_layout = QVBoxLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_layout.addWidget(self.video_label)

        self.overlay = OverlayWidget(self.video_container)
        main_layout.addWidget(self.video_container, stretch=1)

        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(60)
        bottom_bar.setStyleSheet("""
            QFrame { background-color: #111111; border-top: 1px solid #333333; }
            QLabel { color: #ffffff; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold; margin-right: 5px; }
            QComboBox { 
                background-color: #222222; color: #ffffff; 
                border: 1px solid #555555; border-radius: 4px; 
                padding: 4px 10px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QCheckBox { color: #ffffff; font-size: 12px; font-family: 'Segoe UI'; }
        """)
        
        toolbar_layout = QHBoxLayout(bottom_bar)
        toolbar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.setSpacing(15)

        toolbar_layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Two-hand Chord", "Drum Pad (4x4)"])
        self.mode_combo.currentTextChanged.connect(self.change_layout_mode)
        toolbar_layout.addWidget(self.mode_combo)

        snap_check = QCheckBox("Snap")
        snap_check.setChecked(True)
        toolbar_layout.addWidget(snap_check)

        toolbar_layout.addWidget(QLabel("Scale:"))
        scale_combo = QComboBox()
        scale_combo.addItems(["Major", "Minor", "Pentatonic"])
        toolbar_layout.addWidget(scale_combo)

        toolbar_layout.addWidget(QLabel("Wave:"))
        wave_combo = QComboBox()
        wave_combo.addItems(["Triangle", "Sine", "Square", "Sawtooth"])
        toolbar_layout.addWidget(wave_combo)

        toolbar_layout.addWidget(QLabel("Range:"))
        range_combo = QComboBox()
        range_combo.addItems(["3 oct", "4 oct", "5 oct"])
        toolbar_layout.addWidget(range_combo)

        main_layout.addWidget(bottom_bar)

        self.thread = VisionThread(vision_handler, tracker, mapper, midi_out)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.update_overlay_signal.connect(self.overlay.update_zones)
        self.thread.start()

    def change_layout_mode(self, mode_name):
        if mode_name == "Two-hand Chord":
            self.mapper.load_radial_layout()
        elif mode_name == "Drum Pad (4x4)":
            self.mapper.load_drum_pad_layout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.video_container.size())

    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.video_container.width(), self.video_container.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding
        ))

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()