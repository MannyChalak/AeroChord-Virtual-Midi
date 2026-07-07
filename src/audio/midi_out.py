import mido
import logging
from typing import Optional

logger = logging.getLogger("MIDI_Out")

class MidiOutHandler:
    def __init__(self, target_port_name: str = "AeroChord") -> None:
        self.port: Optional[mido.ports.BaseOutput] = None
        available_ports = mido.get_output_names()
        
        if not available_ports:
            logger.error("No MIDI ports found! Is loopMIDI running?")
            return

        matched_port = next((p for p in available_ports if target_port_name.lower() in p.lower()), None)
        try:
            if matched_port:
                self.port = mido.open_output(matched_port)
                logger.info(f"Connected successfully to: {matched_port}")
            else:
                self.port = mido.open_output(available_ports[0])
                logger.warning(f"Target not found. Fallback to: {available_ports[0]}")
        except Exception as e:
            logger.error(f"Failed to open MIDI port. Exception: {e}")

    def send_pitchwheel(self, pitch: int, channel: int = 0) -> None:
        """
        Send Pitch Bend message.
        MIDI standard pitch values range from -8192 (full bend down) to 8191 (full bend up).
        """
        if not self.port: return
        p = max(-8192, min(8191, pitch))
        msg = mido.Message('pitchwheel', pitch=p, channel=channel)
        self.port.send(msg)

    def send_program_change(self, program: int, channel: int = 0) -> None:
        if not self.port: return
        p = max(0, min(127, program))
        msg = mido.Message('program_change', program=p, channel=channel)
        self.port.send(msg)

    def send_note_on(self, note: int, velocity: int = 100, channel: int = 0) -> None:
        if not self.port: return
        n, v = max(0, min(127, note)), max(0, min(127, velocity))
        msg = mido.Message('note_on', note=n, velocity=v, channel=channel)
        self.port.send(msg)

    def send_note_off(self, note: int, velocity: int = 0, channel: int = 0) -> None:
        if not self.port: return
        n = max(0, min(127, note))
        msg = mido.Message('note_off', note=n, velocity=0, channel=channel)
        self.port.send(msg)

    def send_cc(self, control: int, value: int, channel: int = 0) -> None:
        if not self.port: return
        c, v = max(0, min(127, control)), max(0, min(127, value))
        msg = mido.Message('control_change', control=c, value=v, channel=channel)
        self.port.send(msg)

    def release(self) -> None:
        if self.port: self.port.close()