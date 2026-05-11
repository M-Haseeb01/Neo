# tools.py
import mss
import base64
import io
from PIL import Image
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

def capture_screen_b64() -> str:
    """Captures the primary monitor and returns a base64 encoded JPEG."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

class WhiteboardTool(QWidget):
    """Digital Blue-Board UI with Minimize and Close options."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(600, 500)
        
        self.BOARD_BG = "#0F172A"      
        self.HEADER_BG = "#1E293B"     
        self.NEON_CYAN = "#14E7FF"     
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: {self.BOARD_BG};
                border: 3px solid {self.NEON_CYAN};
                border-radius: 10px;
            }}
        """)
        self.main_layout.addWidget(self.container)
        
        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header Bar
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet(f"background-color: {self.HEADER_BG}; border: none; border-bottom: 1px solid {self.NEON_CYAN}; border-radius: 0px;")
        h_layout = QHBoxLayout(header)
        
        title = QLabel("Digital Blue-Board")
        title.setStyleSheet(f"color: {self.NEON_CYAN}; font: bold 13px 'Segoe UI'; border: none; background: transparent;")
        
        # Minimize Button
        min_btn = QPushButton("—")
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.setFixedSize(30, 30)
        min_btn.setStyleSheet(f"""
            QPushButton {{ color: white; font-weight: bold; font-size: 14px; border: none; background: transparent; padding-bottom: 5px; }}
            QPushButton:hover {{ color: {self.NEON_CYAN}; }}
        """)
        min_btn.clicked.connect(self.showMinimized)
        
        # Close Button
        close_btn = QPushButton("✕")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: white; font-weight: bold; font-size: 16px; border: none; background: transparent; }}
            QPushButton:hover {{ color: {self.NEON_CYAN}; }}
        """)
        close_btn.clicked.connect(self.hide)
        
        h_layout.addWidget(title)
        h_layout.addStretch()
        h_layout.addWidget(min_btn)    # Added Minimize button here
        h_layout.addWidget(close_btn)
        inner_layout.addWidget(header)

        # Text Area
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.BOARD_BG};
                color: #FFFFFF;
                font-size: 17px;
                font-family: 'Consolas', 'Segoe UI';
                border: none;
                padding: 20px;
                line-height: 150%;
            }}
        """)
        inner_layout.addWidget(self.text_area)

    def append_text(self, text):
        clean_text = text.replace("<WHITEBOARD>", "").replace("</WHITEBOARD>", "")
        if clean_text:
            if not self.isVisible():
                self.showNormal() # Ensures it restores if minimized
                self.raise_()
                self.activateWindow()
            
            self.text_area.insertPlainText(clean_text)
            scrollbar = self.text_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def update_text(self, text):
        self.text_area.setPlainText(text.strip())
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # Smooth Dragging
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()