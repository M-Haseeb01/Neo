# app.py
import sys
import threading
import json
import math
import struct

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen

import sounddevice as sd
from vosk import Model, KaldiRecognizer

from backend import TTSPipeline, ChatController
from tools import capture_screen_b64, WhiteboardTool
from avatar import _make_avatar_frame

# ─── Constants ────────────────────────────────────────────────────────────────
BG_COLOR   = "#0D1117"
NEON_CYAN  = "#14E7FF"

# Path to your extracted Vosk model folder.
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"

# Vosk STT settings
SAMPLE_RATE    = 16000   
BLOCK_SIZE     = 4000    
SILENCE_RMS    = 50      
SILENCE_SECS   = 2.0     
MAX_RECORD_SEC = 12.0    


# ─── Helper: Custom RMS (Replaces deprecated audioop) ─────────────────────────
def compute_rms(raw_bytes):
    count = len(raw_bytes) // 2
    if count == 0:
        return 0
    shorts = struct.unpack(f"<{count}h", raw_bytes)
    sum_squares = sum(s * s for s in shorts)
    return int(math.sqrt(sum_squares / count))


# ─── Main Widget ──────────────────────────────────────────────────────────────
class NeoApp(QWidget):
    tool_signal   = pyqtSignal(str, str)
    stream_signal = pyqtSignal(str)
    
    # NEW: Safe thread-to-UI communication signals for the microphone
    voice_result_signal = pyqtSignal(str)
    voice_error_signal  = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 230)

        # Hover-only Close Button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setGeometry(175, 5, 20, 20)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton        {{ color: transparent; background: transparent;
                                 border: none; font-weight: bold; font-size: 12px; }}
            QPushButton:hover {{ color: {NEON_CYAN}; }}
        """)
        self.close_btn.clicked.connect(self.close_app)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 20, 15, 15)
        self.main_layout.setSpacing(6)

        self.status_lbl = QLabel("● Booting...")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #FBBF24; font: bold 8pt 'Helvetica';")
        self.main_layout.addWidget(self.status_lbl)

        self.avatar_lbl = QLabel()
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.avatar_lbl)

        input_container = QWidget()
        input_container.setStyleSheet("background: #1E293B; border-radius: 4px;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(6, 2, 6, 2)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask...")
        self.chat_input.setStyleSheet("color: white; border: none; background: transparent; font-size: 9pt;")
        self.chat_input.returnPressed.connect(self.handle_action)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setFixedWidth(20)
        self.mic_btn.setStyleSheet(f"color: {NEON_CYAN}; border: none; background: transparent; font-size: 11pt;")
        self.mic_btn.clicked.connect(self.start_voice_input)

        self.action_btn = QPushButton("▶")
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setFixedWidth(20)
        self.action_btn.setStyleSheet("color: #4ADE80; border: none; background: transparent; font-size: 12pt;")
        self.action_btn.clicked.connect(self.handle_action)

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.mic_btn)
        input_layout.addWidget(self.action_btn)
        self.main_layout.addWidget(input_container)

        self.board_cb = QCheckBox("Solve on Whiteboard")
        self.board_cb.setStyleSheet(f"""
            QCheckBox            {{ color: white; font-size: 8pt; font-weight: bold; }}
            QCheckBox::indicator {{ width: 12px; height: 12px; border-radius: 2px;
                                   background-color: #1E293B; border: 1px solid white; }}
            QCheckBox::indicator:checked {{ background-color: {NEON_CYAN}; }}
        """)
        self.main_layout.addWidget(self.board_cb, alignment=Qt.AlignmentFlag.AlignCenter)

        self.explain_btn = QPushButton("Explain Screen")
        self.explain_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.explain_btn.setStyleSheet(f"""
            QPushButton       {{ background: {NEON_CYAN}; color: #0F172A; font-weight: bold;
                                 border-radius: 4px; padding: 4px; font-size: 8pt; }}
            QPushButton:hover {{ background: #FFFFFF; }}
        """)
        self.explain_btn.clicked.connect(self.explain_screen)
        self.main_layout.addWidget(self.explain_btn)

        self._mode         = "booting"
        self._tick         = 0
        self._blink        = 0
        self.is_processing = False
        self._listening    = False       
        self._vosk_model   = None        

        self.whiteboard = WhiteboardTool()
        
        # Connect all signals securely
        self.tool_signal.connect(self.safe_handle_tools)
        self.stream_signal.connect(self.safe_stream_update)
        self.voice_result_signal.connect(self.on_voice_result)
        self.voice_error_signal.connect(self.on_voice_error)

        self.tts  = TTSPipeline(state_callback=self.set_speaking)
        self.ctrl = ChatController(
            self.tts,
            tool_callback=lambda a, p: self.tool_signal.emit(a, p),
            stream_callback=lambda token: self.stream_signal.emit(token),
        )

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate_frame)
        self.anim_timer.start(50)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(BG_COLOR))
        pen = QPen(QColor(NEON_CYAN))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 15, 15)

    def safe_handle_tools(self, action, payload):
        if action == "whiteboard" and not self.board_cb.isChecked():
            self.whiteboard.update_text(payload)

    def safe_stream_update(self, token):
        if self.board_cb.isChecked():
            self.whiteboard.append_text(token)

    def set_speaking(self, is_speaking):
        QTimer.singleShot(0, lambda: self._update_speaking_state(is_speaking))

    def _update_speaking_state(self, is_speaking):
        if self._mode != "booting":
            self._mode = "speaking" if is_speaking else "idle"

    def close_app(self):
        self.ctrl.stop()
        QApplication.quit()

    def explain_screen(self):
            """Modified: Combines current input text with the screen capture trigger."""
            if self.is_processing:
                return
            
            current_text = self.chat_input.text().strip()
            
            # 1. If the box is empty, use a default prompt.
            if not current_text:
                self.chat_input.setText("Explain what you see on my screen.")
            else:
                # 2. If the user typed something but didn't include a trigger word, 
                # we append it so handle_action() knows to take a screenshot.
                trigger_keywords = ["see", "screen", "look", "where", "explain"]
                if not any(kw in current_text.lower() for kw in trigger_keywords):
                    # Append contextually so the LLM understands it's a visual query
                    self.chat_input.setText(f"{current_text} (looking at my screen)")

            # 3. Trigger the standard action handler
            self.handle_action()

    def handle_action(self):
        if self.is_processing:
            self.ctrl.stop()
            return

        text = self.chat_input.text().strip()
        if not text:
            return

        if self.board_cb.isChecked():
            self.whiteboard.text_area.clear()
            text += " Please provide the detailed answer and math formatted nicely."

        self.chat_input.clear()

        img_b64 = None
        # This check now works for both the dedicated button and manual typing
        if any(kw in text.lower() for kw in ["see", "screen", "look", "where", "explain"]):
            self.status_lbl.setText("● Capturing...")
            self.status_lbl.setStyleSheet("color: #F87171;")
            img_b64 = capture_screen_b64()

        self.status_lbl.setText("● Thinking...")
        self.status_lbl.setStyleSheet("color: #FBBF24;")
        self.ctrl.send(text, img_b64=img_b64)

    # ── Safe UI Callbacks for Microphone ──────────────────────────────────────
    def on_voice_result(self, text):
        """Runs securely on the Main UI Thread when voice recording finishes."""
        self._listening = False
        self.mic_btn.setEnabled(True)
        self.chat_input.setText(text)
        # Give the UI 100ms to visually update before sending
        QTimer.singleShot(100, self.handle_action)

    def on_voice_error(self, err_msg):
        """Runs securely on the Main UI Thread when an error or silence occurs."""
        self._listening = False
        self.mic_btn.setEnabled(True)
        if not self.is_processing:
            self.status_lbl.setText(err_msg)
            if "Error" in err_msg:
                self.status_lbl.setStyleSheet("color: #F87171;")
            else:
                self.status_lbl.setStyleSheet("color: #FBBF24;")
            
            QTimer.singleShot(2500, self.reset_status)

    def reset_status(self):
        if not self.is_processing and not self._listening:
            self.status_lbl.setText("● Idle")
            self.status_lbl.setStyleSheet("color: #4ADE80;")

    # ── Offline voice input (Vosk) ────────────────────────────────────────────
    def _load_vosk_model(self):
        if self._vosk_model is None:
            try:
                self._vosk_model = Model(VOSK_MODEL_PATH)
            except Exception as e:
                print(f"[Vosk] Could not load model from '{VOSK_MODEL_PATH}': {e}")
                self._vosk_model = None
        return self._vosk_model

    def start_voice_input(self):
        if self.is_processing or self._listening:
            return
        self._listening = True
        self.status_lbl.setText("● Listening...")
        self.status_lbl.setStyleSheet(f"color: {NEON_CYAN};")
        self.mic_btn.setEnabled(False)
        threading.Thread(target=self._voice_thread, daemon=True).start()

    def _voice_thread(self):
        model = self._load_vosk_model()
        if model is None:
            self.voice_error_signal.emit("● No STT Model")
            return

        rec = KaldiRecognizer(model, SAMPLE_RATE)

        max_silence_blocks = int(SILENCE_SECS / (BLOCK_SIZE / SAMPLE_RATE))
        max_total_blocks   = int(MAX_RECORD_SEC / (BLOCK_SIZE / SAMPLE_RATE))

        silence_blocks = 0
        speech_started = False   

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
            ) as stream:
                for _ in range(max_total_blocks):
                    data, _ = stream.read(BLOCK_SIZE)
                    raw = bytes(data)
                    rec.AcceptWaveform(raw)

                    # Now uses safe struct-based RMS calculation
                    rms = compute_rms(raw)          
                    print(f"[Mic Volume] {rms}")

                    if rms >= SILENCE_RMS:
                        speech_started = True
                        silence_blocks = 0
                    elif speech_started:
                        silence_blocks += 1

                    if speech_started and silence_blocks >= max_silence_blocks:
                        break

        except Exception as e:
            print(f"[Mic Error] {e}")
            self.voice_error_signal.emit("● Mic Error")
            return

        if not speech_started:
            self.voice_error_signal.emit("● Nothing heard")
            return

        result = json.loads(rec.FinalResult())
        text   = result.get("text", "").strip()
        
        print(f"[Vosk Transcribed] -> '{text}'")

        if text:
            # Emit the successful text to the main UI thread safely
            self.voice_result_signal.emit(text)
        else:
            self.voice_error_signal.emit("● Didn't catch that")

    # ── Animation loop ────────────────────────────────────────────────────────
    def animate_frame(self):
        self._tick  += 1
        self._blink += 1

        if self._mode == "booting":
            if self._tick > 30:
                self._mode = "idle"
            progress = min(1.0, self._tick / 30)
        else:
            progress = 1.0

        backend_busy = (
            self.ctrl.is_generating
            or self.tts.is_playing
            or not self.tts.text_queue.empty()
            or not self.tts.audio_queue.empty()
        )

        if backend_busy and not self.is_processing:
            self.is_processing = True
            self.action_btn.setText("⏹")
            self.action_btn.setStyleSheet("color: #F87171; border: none; background: transparent; font-size: 12pt;")
        elif not backend_busy and self.is_processing:
            self.is_processing = False
            self.status_lbl.setText("● Idle")
            self.status_lbl.setStyleSheet("color: #4ADE80;")
            self.action_btn.setText("▶")
            self.action_btn.setStyleSheet("color: #4ADE80; border: none; background: transparent; font-size: 12pt;")
            self._mode = "idle"

        blink = (self._blink % 90) in range(2, 5)
        q_img = _make_avatar_frame(
            size=100, mode=self._mode, tick=self._tick,
            blink=blink, progress=progress
        )
        self.avatar_lbl.setPixmap(QPixmap.fromImage(q_img))

    # ── Drag support ──────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + diff)
            self.drag_pos = event.globalPosition().toPoint()


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app    = QApplication(sys.argv)
    window = NeoApp()
    window.show()
    sys.exit(app.exec())