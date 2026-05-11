# backend.py
import queue
import re
import threading
import ollama
import sounddevice as sd
from kittentts import KittenTTS
import config

class TTSPipeline:
    def __init__(self, state_callback=None):
        print("[TTS] Loading model…")
        self.tts = KittenTTS(config.TTS_MODEL)
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.state_callback = state_callback
        self.is_playing = False
        threading.Thread(target=self._synth_loop, daemon=True).start()
        threading.Thread(target=self._playback_loop, daemon=True).start()

    def stop(self):
        """Instantly clears queues and stops audio playback."""
        with self.text_queue.mutex:
            self.text_queue.queue.clear()
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()
        sd.stop()
        self.is_playing = False
        if self.state_callback: self.state_callback(False)

    def _synth_loop(self):
        while True:
            text = self.text_queue.get()
            if text is None: break
            try:
                audio = self.tts.generate(text, voice=config.TTS_VOICE, speed=config.TTS_SPEED)
                if audio is not None and len(audio) > 0: self.audio_queue.put(audio)
            except Exception as e: print(f"[TTS Error] {e}")
            finally: self.text_queue.task_done()

    def _playback_loop(self):
        while True:
            audio = self.audio_queue.get()
            if audio is None: break
            
            self.is_playing = True
            if self.state_callback: self.state_callback(True)
            
            sd.play(audio, samplerate=config.SAMPLE_RATE)
            sd.wait() 
            
            self.is_playing = False
            if self.state_callback: self.state_callback(False)
            self.audio_queue.task_done()

    def speak(self, text: str):
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r"[^\x00-\x7F]+", "", text).strip()
        if len(text) > 2: self.text_queue.put(text)

class ChatController:
    def __init__(self, tts: TTSPipeline, tool_callback, stream_callback=None):
        self.tts = tts
        self.tool_callback = tool_callback
        self.stream_callback = stream_callback
        self.history = [{"role": "system", "content": config.SYSTEM_PROMPT}]
        self.abort_flag = False
        self.is_generating = False

    def stop(self):
        """Flags the generation loop to break and stops TTS."""
        self.abort_flag = True
        self.tts.stop()

    def send(self, user_text: str, img_b64: str = None):
        self.abort_flag = False
        self.is_generating = True
        msg = {"role": "user", "content": user_text}
        if img_b64: msg["images"] = [img_b64]
        self.history.append(msg)
        threading.Thread(target=self._stream, args=(user_text,), daemon=True).start()

    def _stream(self, user_text):
        try:
            stream = ollama.chat(model=config.MODEL, messages=self.history, stream=True, options={"temperature": 0.2})
            buf, full_res = "", ""

            for chunk in stream:
                if self.abort_flag: 
                    break
                
                token = chunk["message"]["content"]
                if self.stream_callback: 
                    self.stream_callback(token)
                    
                buf += token; full_res += token
                parts = re.split(r"(?<=[.!?]) +", buf)
                for sentence in parts[:-1]: self.tts.speak(sentence)
                buf = parts[-1]
            
            if not self.abort_flag:
                self.tts.speak(buf)
                self.history.append({"role": "assistant", "content": full_res})
                
                # Fallback extraction if stream is disabled
                wb = re.search(r'<WHITEBOARD>(.*?)</WHITEBOARD>', full_res, re.DOTALL | re.IGNORECASE)
                if wb: self.tool_callback("whiteboard", wb.group(1))

        except Exception as e:
            print(f"[Ollama Error] {e}")
        finally:
            self.is_generating = False