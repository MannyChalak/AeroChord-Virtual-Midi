import numpy as np
import logging
import math
import collections
from typing import List, Tuple, Dict, Any

logger = logging.getLogger("Mapping")

class VirtualZone:
    def __init__(self, name: str, midi_note: int):
        self.name = name
        self.midi_note = midi_note
        self.is_active = False
    def contains(self, x: float, y: float) -> bool:
        raise NotImplementedError

class RadialZone(VirtualZone):
    def __init__(self, name: str, midi_note: int, cx: float, cy: float, inner_r: float, outer_r: float, start_deg: float, end_deg: float):
        super().__init__(name, midi_note)
        self.cx, self.cy = cx, cy
        self.inner_r, self.outer_r = inner_r, outer_r
        self.start_deg, self.end_deg = start_deg, end_deg
        self.start_rad, self.end_rad = math.radians(start_deg), math.radians(end_deg)

    def contains(self, x: float, y: float) -> bool:
        dx, dy = x - self.cx, y - self.cy
        if not (self.inner_r <= math.hypot(dx, dy) <= self.outer_r): return False
        angle = math.atan2(dy, dx)
        if angle < 0: angle += 2 * math.pi
        start, end = self.start_rad % (2 * math.pi), self.end_rad % (2 * math.pi)
        if start < end: return start <= angle <= end
        else: return angle >= start or angle <= end

class GridZone(VirtualZone):
    def __init__(self, name: str, midi_note: int, x: float, y: float, w: float, h: float):
        super().__init__(name, midi_note)
        self.x, self.y, self.w, self.h = x, y, w, h
    def contains(self, px: float, py: float) -> bool:
        return (self.x <= px <= self.x + self.w) and (self.y <= py <= self.y + self.h)

class CenterCircleZone(VirtualZone):
    def __init__(self, name: str, cx: float, cy: float, radius: float):
        super().__init__(name, -1)
        self.cx, self.cy, self.radius = cx, cy, radius
    def contains(self, x: float, y: float) -> bool:
        return math.hypot(x - self.cx, y - self.cy) <= self.radius

class InteractionMapper:
    def __init__(self) -> None:
        self.zones: List[VirtualZone] = []
        # Strictly tracking only Thumb (4) and Index (8)
        self.fingertips: List[int] = [4, 8]
        self.finger_histories: Dict[int, collections.deque] = {tip: collections.deque(maxlen=10) for tip in self.fingertips}
        self.load_radial_layout()

    def load_radial_layout(self, scale_type: str = "Major", is_simple: bool = True, octave: int = 4) -> None:
        self.zones = []
        base_note = (octave + 1) * 12 
        notes_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        if scale_type == "Major": intervals = [0, 2, 4, 5, 7, 9, 11]
        elif scale_type == "Minor": intervals = [0, 2, 3, 5, 7, 8, 10]
        elif scale_type == "Pentatonic": intervals = [0, 2, 4, 7, 9]
        else: intervals = [0, 2, 4, 5, 7, 9, 11]

        active_intervals = intervals if is_simple else list(range(12))
        angle_step = 360 / len(active_intervals)
        inner_radius, outer_radius = 0.08, 0.28

        for i, interval in enumerate(active_intervals):
            start = i * angle_step
            end = (i + 1) * angle_step
            note_val = base_note + interval
            self.zones.append(RadialZone(notes_names[note_val % 12], note_val, 0.2, 0.5, inner_radius, outer_radius, start, end))
        
        self.zones.append(CenterCircleZone("OFF", 0.2, 0.5, inner_radius))

        chords = [("maj", base_note + 12), ("aug", base_note + 13), ("dim", base_note + 14), ("m7", base_note + 15), ("m", base_note + 16)]
        angle_step_chord = 360 / len(chords)
        for i, (name, note) in enumerate(chords):
            start = i * angle_step_chord
            end = (i + 1) * angle_step_chord
            self.zones.append(RadialZone(name, note, 0.8, 0.5, inner_radius, outer_radius, start, end))
        
        self.zones.append(CenterCircleZone("OFF", 0.8, 0.5, inner_radius))

    def load_drum_pad_layout(self, octave: int = 3) -> None:
        self.zones = []
        start_x, start_y, w, h, margin = 0.3, 0.2, 0.08, 0.12, 0.02
        base_note = (octave + 1) * 12
        for row in range(4):
            for col in range(4):
                zx = start_x + col * (w + margin)
                zy = start_y + row * (h + margin)
                self.zones.append(GridZone(f"Pad_{row}{col}", base_note + (row * 4) + col, zx, zy, w, h))

    def _map_z_to_cc(self, z_value: float) -> int:
        normalized_z = np.clip((z_value + 0.15) / 0.25, 0.0, 1.0)
        return int((1.0 - normalized_z) * 127)

    def _calculate_pitch_bend(self, hand: List[Tuple[float, float, float]]) -> int:
        x1, y1, _ = hand[4]
        x2, y2, _ = hand[8]
        dist = math.hypot(x1 - x2, y1 - y2)
        normalized = np.clip((dist - 0.02) / 0.13, 0.0, 1.0)
        return int((normalized * 16383) - 8192)

    def process_landmarks(self, hands_landmarks: List[List[Tuple[float, float, float]]]) -> Dict[str, Any]:
        triggered_events = []
        pitch_val = 0

        if hands_landmarks:
            hand = hands_landmarks[0]
            if len(hand) > 20:
                pitch_val = self._calculate_pitch_bend(hand)
                active_zones_data = {}
                
                # Clear queues smoothly and record interactions
                for tip in self.fingertips:
                    x, y, z = hand[tip]
                    self.finger_histories[tip].append((x, y))
                    z_mapped = self._map_z_to_cc(z)

                    for zone in self.zones:
                        if zone.contains(x, y):
                            if zone.name not in active_zones_data:
                                active_zones_data[zone.name] = {"note": zone.midi_note, "z_mapped": z_mapped}
                            else:
                                active_zones_data[zone.name]["z_mapped"] = max(active_zones_data[zone.name]["z_mapped"], z_mapped)

                for zone in self.zones:
                    if zone.name in active_zones_data:
                        data = active_zones_data[zone.name]
                        if not zone.is_active:
                            triggered_events.append({"zone_name": zone.name, "note": data["note"], "z_mapped": data["z_mapped"], "just_entered": True})
                        else:
                            triggered_events.append({"zone_name": zone.name, "note": data["note"], "z_mapped": data["z_mapped"]})
                        zone.is_active = True
                    else:
                        if zone.is_active:
                            triggered_events.append({"zone_name": zone.name, "note": zone.midi_note, "z_mapped": 0, "just_left": True})
                        zone.is_active = False
        else:
            # Clear histories smoothly if hand disappears
            for tip in self.fingertips:
                if self.finger_histories[tip]:
                    self.finger_histories[tip].popleft()

        return {
            "events": triggered_events,
            "pitch": pitch_val,
            "trails": {k: list(v) for k, v in self.finger_histories.items()}
        }