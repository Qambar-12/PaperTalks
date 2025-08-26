# PaperTalks

AI-powered pipeline that reimagines peer review as engaging podcast conversations, powered by CrewAI and ElevenLabs.

## 🚀 Features

- 📄 **Research paper analysis and summarization** – Automatically digest academic papers into structured insights
- 🎙️ **Natural author–reviewer script generation** – Simulate constructive academic dialogues
- ✨ **Enhanced script refinement** – Polish conversations for flow, clarity, and engagement
- 🗣️ **High-quality voice synthesis with ElevenLabs** – Bring the Author and Reviewer to life
- 🎧 **Professional audio mixing and processing** – Ready-to-publish podcast episodes

---

## ⚙️ Setup

### 1. Clone this repository
```bash
git clone https://github.com/yourusername/PaperTalks.git
cd PaperTalks
```

### 2. Install requirements
```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file with your API keys
```env
AIML_API_KEY=your_aiml_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
SERPER_API_KEY=your_serper_key_here
BEN_VOICE_ID=your-elevenlabs-ben-voice-id
CLAUDIA_VOICE_ID=your-elevenlabs-claudia-voice-id
```

---

## ▶️ Usage

1. Place your research paper in the `knowledge/` directory (or use the sample paper included).
2. Run the podcast generator script:
```bash
python peer_review_podcast.py
```

Find outputs in the `outputs/` directory:

- 📝 Generated scripts
- 🔊 Audio segments
- 🎙️ Final mixed podcast

---

## 🔧 Configuration

- **Voice settings:** Adjust in `tools.py`
- **Agent behaviors:** Modify in `peer_review_podcast.py`
- **Pipeline flow:** Extend via `crew.py`

## Acknowledgments
- **CrewAI**
- **ElevenLabs**