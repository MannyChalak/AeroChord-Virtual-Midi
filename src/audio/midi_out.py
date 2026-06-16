import mido
import logging
from typing import Optional

logger = logging.getLogger("MIDI_Out")

class MidiOutHandler:
    def __init__(self, target_port_name: str = "AeroChord") -> None:
        """
        Connect to loopMIDI virtual port to send signals to DAWs like FL Studio.
        """
        self.port: Optional[mido.ports.BaseOutput] = None
        available_ports = mido.get_output_names()
        
        if not available_ports:
            logger.error("No MIDI ports found! Please open loopMIDI.")
            return

        matched_port = next((p for p in available_ports if target_port_name.lower() in p.lower()), None)

        try:
            if matched_port:
                self.port = mido.open_output(matched_port)
                logger.info(f"Connected to loopMIDI port: {matched_port}")
            else:
                self.port = mido.open_output(available_ports[0])
                logger.warning(f"Fallback to: {available_ports[0]}")
        except Exception as e:
            logger.error(f"Failed to open MIDI port. Exception: {e}")

    def send_note_on(self, note: int, velocity: int = 100, channel: int = 0) -> None:
        if not self.port: return
        msg = mido.Message('note_on', note=max(0, min(127, note)), velocity=max(0, min(127, velocity)), channel=channel)
        self.port.send(msg)

    def send_note_off(self, note: int, velocity: int = 0, channel: int = 0) -> None:
        if not self.port: return
        msg = mido.Message('note_off', note=max(0, min(127, note)), velocity=max(0, min(127, velocity)), channel=channel)
        self.port.send(msg)

    def send_cc(self, control: int, value: int, channel: int = 0) -> None:
        if not self.port: return
        msg = mido.Message('control_change', control=max(0, min(127, control)), value=max(0, min(127, value)), channel=channel)
        self.port.send(msg)

    def release(self) -> None:
        if self.port: self.port.close()