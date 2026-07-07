import cv2
import numpy as np
from PyQt6.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                             QWidget, QComboBox, QCheckBox, QFrame)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from .overlay import OverlayWidget

class VisionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    update_overlay_signal = pyqtSignal(list, set, dict) 

    def __init__(self, vision_handler, tracker, mapper, midi_out) -> None:
        super().__init__()
        self.vision_handler = vision_handler
        self.tracker = tracker
        self.mapper = mapper
        self.midi_out = midi_out
        self._run_flag = True
        self.snap_velocity = True 

    def run(self) -> None:
        while self._run_flag:
            ret, frame = self.vision_handler.get_frame()
            if not ret: continue

            hands_landmarks = self.tracker.process_frame(frame)
            results = self.mapper.process_landmarks(hands_landmarks)
            events = results.get("events", [])
            
            # 1. Pitch Bend Modulation
            self.midi_out.send_pitchwheel(results["pitch"])
            
            # 2. Polyphonic Multi-finger Note Processor
            for event in events:
                current_velocity = 100 if self.snap_velocity else event.get("z_mapped", 100)
                if not self.snap_velocity and current_velocity < 30: current_velocity = 30

                if "just_entered" in event and event["just_entered"]:
                    if event["note"] == -1:
                        self.midi_out.send_cc(control=123, value=0)
                    else:
                        self.midi_out.send_note_on(event["note"], velocity=current_velocity)
                elif "just_left" in event and event["just_left"]:
                    if event["note"] != -1:
                        self.midi_out.send_note_off(event["note"], velocity=0)
                
                if "z_mapped" in event and event["z_mapped"] > 0:
                    self.midi_out.send_cc(control=1, value=event["z_mapped"])
            
            current_active_zones = {z.name for z in self.mapper.zones if z.is_active}
            self.update_overlay_signal.emit(self.mapper.zones, current_active_zones, results.get("trails", {}))
            self.change_pixmap_signal.emit(frame)

    def stop(self) -> None:
        self._run_flag = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self, vision_handler, tracker, mapper, midi_out) -> None:
        super().__init__()
        self.mapper = mapper
        self.midi_out = midi_out
        self.setWindowTitle("AeroChord - Pro Instrument")
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
            QLabel { color: #ffffff; font-family: 'Segoe UI'; font-size: 11px; font-weight: bold; margin-left: 10px; margin-right: 5px; }
            QComboBox { background-color: #222222; color: #ffffff; border: 1px solid #555555; border-radius: 4px; padding: 4px 8px; font-size: 11px;}
            QCheckBox { color: #ffffff; font-size: 11px; font-family: 'Segoe UI'; margin-right: 10px;}
        """)
        
        toolbar_layout = QHBoxLayout(bottom_bar)
        toolbar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        toolbar_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Two-hand Chord", "Drum Pad (4x4)"])
        self.mode_combo.currentTextChanged.connect(self.update_layout_parameters)
        toolbar_layout.addWidget(self.mode_combo)

        self.simple_check = QCheckBox("Simple Mode")
        self.simple_check.setChecked(True)
        self.simple_check.stateChanged.connect(self.update_layout_parameters)
        toolbar_layout.addWidget(self.simple_check)

        self.snap_check = QCheckBox("Snap (Fixed Vel)")
        self.snap_check.setChecked(True)
        self.snap_check.stateChanged.connect(self.update_thread_parameters)
        toolbar_layout.addWidget(self.snap_check)

        # Explicit Sustain Checkbox
        self.sustain_check = QCheckBox("Sustain Pedal")
        self.sustain_check.setChecked(False)
        self.sustain_check.stateChanged.connect(self.toggle_sustain)
        toolbar_layout.addWidget(self.sustain_check)

        toolbar_layout.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["Major", "Minor", "Pentatonic"])
        self.scale_combo.currentTextChanged.connect(self.update_layout_parameters)
        toolbar_layout.addWidget(self.scale_combo)

        toolbar_layout.addWidget(QLabel("Range:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["Octave 3", "Octave 4", "Octave 5"])
        self.range_combo.setCurrentIndex(1) 
        self.range_combo.currentTextChanged.connect(self.update_layout_parameters)
        toolbar_layout.addWidget(self.range_combo)

        toolbar_layout.addWidget(QLabel("Wave:"))
        self.wave_combo = QComboBox()
        self.wave_combo.addItems(["Piano", "Synth Square", "Synth Saw", "Warm Pad"])
        self.wave_combo.currentIndexChanged.connect(self.change_instrument)
        toolbar_layout.addWidget(self.wave_combo)

        main_layout.addWidget(bottom_bar)

        self.thread = VisionThread(vision_handler, tracker, mapper, midi_out)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.update_overlay_signal.connect(self.overlay.update_zones)
        self.thread.start()

    def update_thread_parameters(self) -> None:
        self.thread.snap_velocity = self.snap_check.isChecked()

    def toggle_sustain(self) -> None:
        """Manually trigger the MIDI Sustain CC."""
        if self.sustain_check.isChecked():
            self.midi_out.send_cc(control=64, value=127) # Sustain ON
        else:
            self.midi_out.send_cc(control=64, value=0)   # Sustain OFF

    def change_instrument(self, index: int) -> None:
        programs = [0, 80, 81, 88]
        self.midi_out.send_program_change(programs[index])

    def update_layout_parameters(self) -> None:
        mode = self.mode_combo.currentText()
        selected_octave = int(self.range_combo.currentText()[-1])

        if mode == "Drum Pad (4x4)":
            self.mapper.load_drum_pad_layout(octave=selected_octave)
        else:
            selected_scale = self.scale_combo.currentText()
            is_simple = self.simple_check.isChecked()
            self.mapper.load_radial_layout(
                scale_type=selected_scale, 
                is_simple=is_simple, 
                octave=selected_octave
            )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.overlay.resize(self.video_container.size())

    def update_image(self, cv_img: np.ndarray) -> None:
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_img).scaled(
            self.video_container.width(), self.video_container.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding
        ))

    def closeEvent(self, event) -> None:
        self.thread.stop()
        event.accept()