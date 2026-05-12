```markdown
# 🎓 NEO: Local-First Multimodal AI Tutor

**Built for the Gemma 4 Good Hackathon (Future of Education Track)**

NEO is an offline-first, multimodal educational assistant designed to bridge the "Homework Gap." While cloud-based tutors require high-bandwidth internet and expensive subscriptions, NEO runs entirely locally on consumer-grade hardware. By leveraging Google's **Gemma 4**, NEO provides a fully private, interactive tutoring experience that can see your screen, speak to you, and write complex equations on a dedicated Digital Blue-Board.

---

## ✨ Core Features

* **🧠 100% Local Inference:** Powered by Gemma 4 (e2b/e4b) via Ollama. No cloud APIs, no data harvesting, and no internet required after setup.
* **🗣️ Real-time Voice (STT & TTS):** Hands-free learning using Vosk for offline speech recognition and KittenTTS for rapid, pipelined audio playback.
* **📝 Digital Blue-Board:** To prevent cognitive overload, Neo extracts technical reasoning (math, code, physics) using `<WHITEBOARD>` tags and renders it on a dedicated visual interface, separate from the chat.
* **👁️ Screen-Aware Vision:** Neo uses local screen capture to "see" what the student is working on, allowing for contextual questions without manual uploads.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* **Python 3.10+**
* **Ollama:** Install [Ollama](https://ollama.com/) to run the Gemma 4 model locally.

### 2. Install the Model
Open your terminal and pull the optimized Gemma 4 model:
```bash
ollama run gemma4:e2b

```

### 3. Install Python Dependencies

Clone this repository and install the required packages:

```bash
git clone [https://github.com/yourusername/neo-tutor.git](https://github.com/yourusername/neo-tutor.git)
cd neo-tutor
pip install -r requirements.txt

```

### 4. ⚠️ CRITICAL: Download Audio Models (Vosk & KittenTTS)

Because GitHub has a strict 100MB file limit, the AI audio models are not included in this repository. You must download them manually to make NEO speak and listen.

1. **Download Vosk (Speech-to-Text):**
* Download the lightweight model here: [Vosk English Model (40MB)](https://www.google.com/search?q=https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
* Extract the zip and place the `vosk-model-small-en-us-0.15` folder directly into your main project directory.


2. **Download KittenTTS (Text-to-Speech):**
* Download the TTS engine here: [INSERT YOUR KITTENTTS LINK HERE]
* Extract the folder and place it directly into your main project directory.



### 5. Run NEO

Once your models are in place, start the application:

```bash
python app.py

```

---

## 📂 Project Structure

* **`app.py`**: The main PyQt6 application, handling the UI, Digital Blue-Board rendering, and multi-threaded event loops.
* **`backend.py`**: The logic layer. Contains the `ChatController` for Ollama streaming and the `TTSPipeline` for asynchronous audio playback.
* **`config.py`**: Centralized configuration file for easily swapping models, tweaking TTS speeds, and modifying the system prompt.

```

```
