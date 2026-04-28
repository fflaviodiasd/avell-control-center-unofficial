import collections
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRectF

class CpuAreaChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.history = collections.deque([0]*60, maxlen=60)
        
    def update_value(self, value):
        self.history.append(value)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        # Background
        painter.fillRect(rect, QColor("#1a1a1a"))
        
        if len(self.history) < 2:
            return
            
        path = QPainterPath()
        step = w / (len(self.history) - 1)
        
        path.moveTo(0, h)
        for i, val in enumerate(self.history):
            x = i * step
            y = h - (val / 100.0 * h)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
                
        # To close the area
        path.lineTo(w, h)
        path.lineTo(0, h)
        
        # Fill
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(0, 122, 204, 180))
        gradient.setColorAt(1.0, QColor(0, 122, 204, 20))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        
        # Line
        line_path = QPainterPath()
        for i, val in enumerate(self.history):
            x = i * step
            y = h - (val / 100.0 * h)
            if i == 0:
                line_path.moveTo(x, y)
            else:
                line_path.lineTo(x, y)
                
        pen = QPen(QColor("#00aaff"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(line_path)

class RamStackedBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)
        self.used_pct = 0
        
    def update_value(self, used_pct):
        self.used_pct = used_pct
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # Background (Free RAM)
        painter.setBrush(QColor("#3d3d3d"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 4, 4)
        
        # Used RAM
        used_w = rect.width() * (self.used_pct / 100.0)
        if used_w > 0:
            used_rect = QRectF(rect.x(), rect.y(), used_w, rect.height())
            painter.setBrush(QColor("#ff5555")) # Red for RAM
            painter.drawRoundedRect(used_rect, 4, 4)

class DiskDonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(100, 100)
        self.used_pct = 0
        self.text = "0%"
        
    def update_value(self, used_pct, text):
        self.used_pct = used_pct
        self.text = text
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        size = min(rect.width(), rect.height()) - 20
        x = (rect.width() - size) / 2
        y = (rect.height() - size) / 2
        
        draw_rect = QRectF(x, y, size, size)
        
        # Background arc
        pen_bg = QPen(QColor("#2d2d2d"), 15)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(draw_rect, 0, 360 * 16)
        
        # Used arc
        pen_fg = QPen(QColor("#ffb86c"), 15) # Orange for Disk
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        span_angle = int(-self.used_pct / 100.0 * 360 * 16)
        # Qt starts at 3 o'clock. 90*16 is 12 o'clock. Negative angle draws clockwise.
        painter.drawArc(draw_rect, 90 * 16, span_angle)
        
        # Text
        painter.setPen(QColor("#f8f8f2"))
        font = QFont("Ubuntu", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)

class NetMirroredChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.dl_history = collections.deque([0]*60, maxlen=60)
        self.ul_history = collections.deque([0]*60, maxlen=60)
        
    def update_values(self, dl, ul):
        self.dl_history.append(dl)
        self.ul_history.append(ul)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        mid_y = h / 2.0
        
        painter.fillRect(rect, QColor("#1a1a1a"))
        
        # Center line
        painter.setPen(QPen(QColor("#555555"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, int(mid_y), w, int(mid_y))
        
        # Dynamic scale
        max_val = max(max(self.dl_history), max(self.ul_history), 1024)
        
        step = w / (len(self.dl_history) - 1)
        
        # Draw Download (Top)
        path_dl = QPainterPath()
        path_dl.moveTo(0, mid_y)
        for i, val in enumerate(self.dl_history):
            x = i * step
            y = mid_y - (val / max_val * mid_y)
            path_dl.lineTo(x, y)
        path_dl.lineTo(w, mid_y)
        
        painter.setBrush(QColor(80, 250, 123, 100)) # Green
        painter.setPen(QPen(QColor("#50fa7b"), 2))
        painter.drawPath(path_dl)
        
        # Draw Upload (Bottom)
        path_ul = QPainterPath()
        path_ul.moveTo(0, mid_y)
        for i, val in enumerate(self.ul_history):
            x = i * step
            y = mid_y + (val / max_val * mid_y)
            path_ul.lineTo(x, y)
        path_ul.lineTo(w, mid_y)
        
        painter.setBrush(QColor(189, 147, 249, 100)) # Purple
        painter.setPen(QPen(QColor("#bd93f9"), 2))
        painter.drawPath(path_ul)
