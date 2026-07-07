from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QRectF
import math

from logic.mapping import RadialZone, GridZone, CenterCircleZone

class OverlayWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.zones = []
        self.active_zone_names = set()
        self.trails = {}

    def update_zones(self, zones: list, active_zone_names: set, trails: dict) -> None:
        """Update interface parameters from the background thread logic."""
        self.zones = zones
        self.active_zone_names = active_zone_names
        self.trails = trails
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        width, height = self.width(), self.height()
        base_size = min(width, height)

        # 1. Draw Virtual Interaction Zones
        font_zones = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font_zones)
        for zone in self.zones:
            is_active = zone.name in self.active_zone_names
            color_fill = QColor(255, 140, 0, 180) if is_active else QColor(30, 30, 30, 150)
            color_text = QColor(255, 255, 255, 255) if is_active else QColor(200, 200, 200, 180)

            if isinstance(zone, RadialZone):
                self._draw_radial(painter, zone, width, height, base_size, color_fill, color_text)
            elif isinstance(zone, GridZone):
                self._draw_grid(painter, zone, width, height, color_fill, color_text)
            elif isinstance(zone, CenterCircleZone):
                self._draw_center(painter, zone, width, height, base_size, is_active)

        # 2. Draw Thin Continuous Vector Lines for Finger Trails
        if self.trails:
            painter.setPen(QPen(QColor(0, 255, 100, 200), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for tip, points in self.trails.items():
                if len(points) > 1:
                    path = QPainterPath()
                    path.moveTo(points[0][0] * width, points[0][1] * height)
                    for pt in points[1:]:
                        path.lineTo(pt[0] * width, pt[1] * height)
                    painter.drawPath(path)

    def _draw_radial(self, painter, zone, w, h, base_size, color_fill, color_text):
        cx, cy = zone.cx * w, zone.cy * h
        ir, orad = zone.inner_r * base_size, zone.outer_r * base_size
        mid_r = (ir + orad) / 2.0
        pen_width = orad - ir
        
        rect = QRectF(cx - mid_r, cy - mid_r, mid_r * 2, mid_r * 2)
        pen = QPen(color_fill, pen_width)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        
        start_angle = -int(zone.start_deg * 16)
        span_angle = -int((zone.end_deg - zone.start_deg) * 16)
        painter.drawArc(rect, start_angle, span_angle)
        
        painter.setPen(QPen(QColor(0, 0, 0, 200), 2))
        painter.drawArc(rect, start_angle, span_angle)

        mid_angle_rad = math.radians((zone.start_deg + zone.end_deg) / 2.0)
        text_x = cx + mid_r * math.cos(mid_angle_rad)
        text_y = cy + mid_r * math.sin(mid_angle_rad)
        
        painter.setPen(QPen(color_text))
        text_rect = QRectF(text_x - 20, text_y - 15, 40, 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, zone.name)

    def _draw_grid(self, painter, zone, w, h, color_fill, color_text):
        x, y = zone.x * w, zone.y * h
        pad_w, pad_h = zone.w * w, zone.h * h
        rect = QRectF(x, y, pad_w, pad_h)
        
        painter.setPen(QPen(QColor(50, 50, 50, 200), 2))
        painter.setBrush(QBrush(color_fill))
        painter.drawRoundedRect(rect, 10.0, 10.0)
        painter.setPen(QPen(color_text))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zone.name)

    def _draw_center(self, painter, zone, w, h, base_size, is_active):
        cx, cy = zone.cx * w, zone.cy * h
        r = zone.radius * base_size
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        
        if is_active:
            painter.setBrush(QBrush(QColor(255, 50, 50, 200)))
            text_color = Qt.GlobalColor.white
        else:
            painter.setBrush(QBrush(QColor(15, 15, 15, 230)))
            text_color = QColor(150, 150, 150)
            
        painter.setPen(QPen(QColor(50, 50, 50), 2))
        painter.drawEllipse(rect)
        
        painter.setPen(QPen(text_color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zone.name)