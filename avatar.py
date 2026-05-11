# avatar.py
from PyQt6.QtGui import QImage, QPainter, QColor, QBrush
from PyQt6.QtCore import Qt
import math

def _make_avatar_frame(size: int = 100, mode: str = "idle", tick: int = 0, blink: bool = False, progress: float = 1.0) -> QImage:
    """Procedural cute square neon-cyan eyes."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(0, 0, 0, 0)) # Transparent canvas
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    cx, cy = size // 2, size // 2
    
    # Exact #14E7FF Color translation (Neon Cyan)
    eye_color = QColor(20, 231, 255) 
    if mode == "booting":
        eye_color.setAlpha(int(255 * progress))
    
    eye_w = 20
    eye_h = 20 
    
    # Blink logic
    if blink: 
        eye_h = 4 
    
    # Speak pulsing logic
    if mode == "speaking":
        eye_h += int(math.sin(tick * 0.6) * 10)
        
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(eye_color))
    
    # Left Eye
    painter.drawRoundedRect(cx - 30, cy - eye_h // 2, eye_w, eye_h, 4, 4)
    # Right Eye
    painter.drawRoundedRect(cx + 10, cy - eye_h // 2, eye_w, eye_h, 4, 4)
    
    painter.end()
    return img