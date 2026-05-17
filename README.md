# NEO: Offline Multimodal AI Tutor

> Gemma 4 sees your screen, explains concepts aloud, and writes step-by-step working on a live Digital Blue-Board. No internet. No GPU. No cost.

---

## What It Does

NEO is a fully offline AI tutor that runs on consumer hardware. Point it at anything on your screen — a math problem, a code error, a diagram — speak your question, and NEO explains it like a smart friend while writing the full working on a dedicated whiteboard.

- **Screen-aware** — captures your screen directly, no manual uploads
- **Dual output** — speaks the summary, writes the steps simultaneously  
- **100% offline** — Gemma 4 via Ollama, Vosk STT, KittenTTS. Zero cloud calls
- **No GPU required** — runs on CPU, tested on 8GB RAM machines

---

## Quick Start

### 1. Install Ollama and pull the model

```bash
ollama pull gemma4:e2b
```

### 2. Clone and install dependencies

```bash
git clone https://github.com/M-Haseeb01/Neo.git
cd Neo
pip install -r requirements.txt
```

### 3. Download audio models

GitHub's 100MB limit means some audio models ship separately.

#### Vosk (Speech-to-Text)

Download:
https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

Extract the folder and place it in the project root.

---

#### KittenTTS (Text-to-Speech)

Install directly from the official GitHub release:

```bash
pip install https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl
```

Optional dependencies:

```bash
pip install soundfile numpy
```

For Windows users, install eSpeak NG and set:

```python
os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
```

### 4. Run

```bash
python app.py
```

CC-BY 4.0 · Muhammad Haseeb

