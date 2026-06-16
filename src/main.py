import sys
import logging
from PyQt6.QtWidgets import QApplication

# Import modular components
from core.vision import WebcamHandler
from core.tracker import HandTracker
from audio.midi_out import MidiOutHandler
from logic.mapping import InteractionMapper
from ui.main_window import MainWindow

# Global logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(name)s - %(message)s')
logger = logging.getLogger("AeroChord_Main")

def main():
    logger.info("Starting AeroChord Initialization...")
    
    # 1. Initialize all core engine handlers
    vision = WebcamHandler(camera_index=0)
    tracker = HandTracker()
    mapper = InteractionMapper()
    midi_out = MidiOutHandler(target_port_name="AeroChord")

    # 2. Initialize PyQt Application
    app = QApplication(sys.argv)
    
    # 3. Create Main Window and inject dependencies
    window = MainWindow(vision, tracker, mapper, midi_out)
    window.show()

    # 4. Start Event Loop
    logger.info("AeroChord GUI is running. Move your hands in front of the camera!")
    exit_code = app.exec()

    # 5. Cleanup resources gracefully on exit
    logger.info("Shutting down resources...")
    vision.release()
    tracker.release()
    midi_out.release()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()