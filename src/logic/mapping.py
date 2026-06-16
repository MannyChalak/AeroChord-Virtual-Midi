import numpy as np
import logging
import math
from typing import List, Tuple, Dict, Any

logger = logging.getLogger("Mapping")

class VirtualZone:
    def __init__(self, name: str, midi_note: int):
        self.name = name
        self.midi_note = midi_note
        self.is_active = False

    def contains(self, x: float, y: float) -> bool:
        """To be overridden by subclasses."""
        raise NotImplementedError

class RadialZone(VirtualZone):
    def __init__(self, name: str, midi_note: int, cx: float, cy: float, inner_r: float, outer_r: float, start_deg: float, end_deg: float):
        super().__init__(name, midi_note)
        self.cx = cx
        self.cy = cy
        self.inner_r = inner_r
        self.outer_r = outer_r
        
        self.start_deg = start_deg
        self.end_deg = end_deg
    
        self.start_rad = math.radians(start_deg)
        self.end_rad = math.radians(end_deg)

    def contains(self, x: float, y: float) -> bool:
        dx = x - self.cx
        dy = y - self.cy
        dist = math.hypot(dx, dy)

        if not (self.inner_r <= dist <= self.outer_r):
            return False

        angle = math.atan2(dy, dx)
        if angle < 0:
            angle += 2 * math.pi

        start = self.start_rad % (2 * math.pi)
        end = self.end_rad % (2 * math.pi)

        if start < end:
            return start <= angle <= end
        else:
            return angle >= start or angle <= end

class GridZone(VirtualZone):
    def __init__(self, name: str, midi_note: int, x: float, y: float, w: float, h: float):
        super().__init__(name, midi_note)
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def contains(self, px: float, py: float) -> bool:
        return (self.x <= px <= self.x + self.w) and (self.y <= py <= self.y + self.h)

class InteractionMapper:
    def __init__(self):
        self.zones: List[VirtualZone] = []
        self.load_radial_layout() 
        logger.info("Interaction Mapper upgraded to support advanced polygon geometry.")

    def load_radial_layout(self):
        self.zones = []
        
        notes = [("C", 60), ("D", 62), ("E", 64), ("F", 65), ("G", 67), ("A", 69), ("B", 71)]
        angle_step = 360 / len(notes)
        for i, (name, note) in enumerate(notes):
            start = i * angle_step
            end = (i + 1) * angle_step
            self.zones.append(RadialZone(name, note, 0.2, 0.5, 0.12, 0.35, start, end))


        chords = [("maj", 72), ("aug", 73), ("dim", 74), ("m7", 75), ("m", 76)]
        angle_step_chord = 360 / len(chords)
        for i, (name, note) in enumerate(chords):
            start = i * angle_step_chord
            end = (i + 1) * angle_step_chord
            self.zones.append(RadialZone(name, note, 0.8, 0.5, 0.12, 0.35, start, end))

    def load_drum_pad_layout(self):
        self.zones = []
        start_x, start_y = 0.3, 0.2
        w, h = 0.08, 0.12
        margin = 0.02
        base_note = 36 # Kick drum in GM standard
        
        for row in range(4):
            for col in range(4):
                zx = start_x + col * (w + margin)
                zy = start_y + row * (h + margin)
                note = base_note + (row * 4) + col
                self.zones.append(GridZone(f"Pad_{row}{col}", note, zx, zy, w, h))

    def _map_z_to_cc(self, z_value: float) -> int:
        normalized_z = np.clip((z_value + 0.15) / 0.25, 0.0, 1.0)
        return int((1.0 - normalized_z) * 127)

    def process_landmarks(self, hands_landmarks):
        triggered_events = []
        INDEX_FINGER_TIP = 8
        active_zone_names_this_frame = set()

        for hand in hands_landmarks:
            if len(hand) > INDEX_FINGER_TIP:
                x, y, z = hand[INDEX_FINGER_TIP]
                cc_value = self._map_z_to_cc(z)

                for zone in self.zones:
                    if zone.contains(x, y):
                        active_zone_names_this_frame.add(zone.name)
                        triggered_events.append({
                            "zone_name": zone.name,
                            "note": zone.midi_note,
                            "cc_value": cc_value,
                            "just_entered": not zone.is_active
                        })

        for zone in self.zones:
            if zone.name in active_zone_names_this_frame:
                zone.is_active = True
            else:
                if zone.is_active:
                    triggered_events.append({
                        "zone_name": zone.name,
                        "note": zone.midi_note,
                        "cc_value": 0,
                        "just_left": True
                    })
                zone.is_active = False

        return triggered_events