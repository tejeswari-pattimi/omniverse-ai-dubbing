# 🛸 Omniverse: Universal AI Video Language Transmutation Engine

An end-to-end, privacy-focused, and 100% local AI video dubbing pipeline. **Omniverse** automatically extracts audio, transcribes dialogue, translates source speech from any language into English, assigns distinct neural voices to multiple speakers, and merges the new audio back onto the original video track.

---

## 🔑 Key Features
* **Zero Cloud Dependency:** Runs 100% locally on your machine with no external API keys or subscription fees.
* **Universal Auto-Detection:** Powered by OpenAI's Whisper AI to automatically recognize and translate multi-lingual speech.
* **Multi-Speaker Neural Routing:** Dynamically rotates through a pool of 16+ distinct male, female, and younger voices based on dialogue segment timestamps.
* **Streamlined Multiplexing:** Uses low-level `FFmpeg` subprocess calls for seamless audio extraction and video container stitching.

---

## 🛠️ Tech Stack
* **Backend:** Python, Flask
* **Speech-to-Text & Translation:** OpenAI Whisper (`small` model)
* **Text-to-Speech Engine:** Edge-TTS
* **Media Processing:** FFmpeg
* **Frontend:** HTML5, CSS3, JavaScript

---

## 🚀 Quick Start Guide

### 1. Prerequisites
Ensure you have **Python** and **FFmpeg** installed and added to your system `PATH`.

### 2. Installation
Clone the repository and install required Python packages:
```bash
git clone [https://github.com/YOUR_USERNAME/omniverse-ai-dubbing.git](https://github.com/YOUR_USERNAME/omniverse-ai-dubbing.git)
cd omniverse-ai-dubbing
pip install flask whisper edge-tts torch torchvision opencv-python librosa