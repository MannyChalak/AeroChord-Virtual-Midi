from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF
import math
from logic.mapping import RadialZone, GridZone

class OverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.zones = []
        self.active_zone_names = set()

    def update_zones(self, zones, active_zone_names):
        self.zones = zones
        self.active_zone_names = active_zone_names
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        width = self.width()
        height = self.height()
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font)

        base_size = min(width, height)

        for zone in self.zones:
            is_active = zone.name in self.active_zone_names
            
            if is_active:
                color_fill = QColor(255, 140, 0, 180)
                color_text = QColor(255, 255, 255, 255)
            else:
                color_fill = QColor(30, 30, 30, 150)
                color_text = QColor(200, 200, 200, 180)

            if isinstance(zone, RadialZone):
                self._draw_radial(painter, zone, width, height, base_size, color_fill, color_text)
            elif isinstance(zone, GridZone):
                self._draw_grid(painter, zone, width, height, color_fill, color_text)

    def _draw_radial(self, painter, zone, w, h, base_size, color_fill, color_text):
        cx = zone.cx * w
        cy = zone.cy * h
        
        ir = zone.inner_r * base_size
        orad = zone.outer_r * base_size
        
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
        x = zone.x * w
        y = zone.y * h
        pad_w = zone.w * w
        pad_h = zone.h * h
        
        rect = QRectF(x, y, pad_w, pad_h)
        
        painter.setPen(QPen(QColor(50, 50, 50, 200), 2))
        painter.setBrush(QBrush(color_fill))
        
        painter.drawRoundedRect(rect, 10.0, 10.0)
        
        painter.setPen(QPen(color_text))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, zone.name)