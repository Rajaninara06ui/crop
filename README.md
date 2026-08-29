# 🌾 Multilingual AI Farmer Advisory Assistant — Backend

A production-style, modular FastAPI backend for the **Multilingual AI Farmer Advisory Assistant**.
The system empowers farmers to ask agricultural queries using **Text or Voice** in their native Indian language, retrieve grounded factual agricultural knowledge via **RAG (Retrieval-Augmented Generation)**, detect crop diseases from leaf photographs, and receive synthesized voice and structured agricultural guidance.

---

## 🏗️ Architecture Concept

```text
                    FARMER
                       │
              Text / Voice / Image
                       │
                       ▼
                React Frontend
                       │
                       ▼
                 FastAPI API
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Voice Service   Translation    Disease Service
        │              │              │
        ▼              ▼              ▼
       STT          Language        ML Model
                       │
                       ▼
                Advisory Service
                       │
              ┌────────┴────────┐
              ▼                 ▼
          RAG System          LLM
              │                 │
              └────────┬────────┘
                       ▼
                Safety Service
                       │
                       ▼
              Response Formatter
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
           Text                 TTS
             │                   │
             └─────────┬─────────┘
                       ▼
                    Farmer
```

---

## 🌐 Supported Languages (8 Indian Languages + English)

| Language Code | Language Name | Script |
| :--- | :--- | :--- |
| `en` | English | Latin |
| `te` | Telugu | Telugu |
| `hi` | Hindi | Devanagari |
| `ta` | Tamil | Tamil |
| `kn` | Kannada | Kannada |
| `ml` | Malayalam | Malayalam |
| `mr` | Marathi | Devanagari |
| `bn` | Bengali | Bengali |

---

## 🚀 Core Features

- **FastAPI Async Pipeline**: High-throughput asynchronous endpoints with non-blocking I/O.
- **RAG Agricultural Grounding**: Document loader, chunker, vector store (FAISS/Mock), and semantic retriever with similarity scoring and source citations.
- **Pluggable LLM Providers**: OpenAI, Google Gemini, Anthropic, or Zero-API Mock Mode (`MOCK_MODE=true`).
- **Voice Transcription (STT)**: Whisper API or Local Whisper for audio inputs (`WAV`, `MP3`, `M4A`, `WebM`).
- **Text-to-Speech (TTS)**: Synthesizes spoken advisory responses in the farmer's target language.
- **Crop Disease Detection**: Leaf image upload with confidence scoring, symptom extraction, treatment recommendations, and low-confidence expert escalation.
- **Safety Validation Layer**: Guards against hazardous chemical dosages, unverified claims, and forces expert escalation disclaimers.
- **JWT Authentication & History**: User registration/login, password hashing via bcrypt, conversation history search and persistence in PostgreSQL.
- **Complete Mock Mode**: Full demo capabilities without external API keys or paid credits.

---

## 📁 Modular Directory Structure

```text
backend/
├── app/
│   ├── main.py                     # FastAPI application factory & middlewares
│   ├── api/
│   │   ├── dependencies.py         # JWT and DB session dependencies
│   │   └── routes/
│   │       ├── auth.py             # POST /auth/register, /login, GET /me
│   │       ├── query.py            # POST /query (Main advisory RAG endpoint)
│   │       ├── voice.py            # POST /voice/transcribe
│   │       ├── disease.py          # POST /disease/detect
│   │       ├── translation.py      # POST /translate
│   │       ├── tts.py              # POST /tts
│   │       ├── history.py          # GET /history, GET /history/{id}, DELETE
│   │       ├── knowledge.py        # GET /knowledge/categories, /search
│   │       └── feedback.py         # POST /feedback
│   ├── core/
│   │   ├── config.py               # Pydantic Settings & environment variables
│   │   ├── security.py             # JWT token creation & bcrypt password hashing
│   │   └── logging.py              # Structured logging & request ID tracking
│   ├── database/
│   │   └── database.py             # Async SQLAlchemy engine & session maker
│   ├── models/                     # SQLAlchemy models (User, Conversation, Message, etc.)
│   ├── schemas/                    # Pydantic validation schemas
│   ├── services/                   # Business logic (Advisory, LLM, RAG, Disease, Voice, TTS)
│   ├── rag/                        # Document loader, chunker, embeddings, vector store, retriever
│   ├── utils/                      # Language, file, and validator helpers
│   └── data/
│       ├── languages.py            # Centralized language configuration
│       └── sample_knowledge/       # Curated demo agricultural knowledge documents
├── scripts/
│   └── ingest_knowledge.py         # Knowledge base ingestion CLI script
├── tests/                          # Complete pytest test suite
├── .env.example                    # Environment variable template
├── Dockerfile                      # Production Docker container
├── docker-compose.yml              # FastAPI + PostgreSQL docker-compose
└── requirements.txt                # Pinned dependencies
```

---

## ⚡ Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- (Optional) PostgreSQL 15+ or Docker

### 2. Setup Virtual Environment
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```
*Note: `MOCK_MODE=true` is enabled by default. The system works immediately without setting API keys.*

### 5. Ingest Knowledge Base (Optional in Mock Mode)
```bash
python scripts/ingest_knowledge.py
```

### 6. Run Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive Swagger documentation.

---

## 🐳 Docker Deployment

To launch the complete stack with PostgreSQL:
```bash
docker compose up --build
```

---

## 🔌 Frontend Integration (React + Vite + TypeScript)

Set your frontend API base URL to `http://localhost:8000/api`.

### Key Frontend Endpoints:

#### 1. Ask Advisory Question (`POST /api/query`)
```ts
const response = await fetch("http://localhost:8000/api/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: "నా టమోటా ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
    language: "te",
    crop: "tomato"
  })
});
const data = await response.json();
```

#### 2. Transcribe Voice (`POST /api/voice/transcribe`)
```ts
const formData = new FormData();
formData.append("audio", audioBlob, "farmer_audio.wav");
formData.append("language", "te");

const response = await fetch("http://localhost:8000/api/voice/transcribe", {
  method: "POST",
  body: formData
});
const data = await response.json();
// data.text => "నా టమోటా ఆకులు..."
```

#### 3. Detect Crop Disease (`POST /api/disease/detect`)
```ts
const formData = new FormData();
formData.append("image", imageFile);
formData.append("crop", "tomato");

const response = await fetch("http://localhost:8000/api/disease/detect", {
  method: "POST",
  body: formData
});
const data = await response.json();
```

#### 4. Play Text-to-Speech (`POST /api/tts`)
```ts
const response = await fetch("http://localhost:8000/api/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    text: advisoryAnswer,
    language: "te"
  })
});
const audioBlob = await response.blob();
const audioUrl = URL.createObjectURL(audioBlob);
new Audio(audioUrl).play();
```

---

## 🧪 Running Tests

Execute the automated test suite covering authentication, RAG retrieval, advisory pipeline, disease detection, voice transcription, and conversation history:

```bash
pytest tests/ -v
```

---

## 🛡️ Safety & Production Rules
- **No Hallucinated Sources**: The system returns only citations directly retrieved from the vector knowledge base.
- **Chemical Safety**: Flags prohibited pesticide terms and attaches mandatory protective gear & dosage disclaimers.
- **Expert Escalation**: When confidence is below `0.70`, the system explicitly advises the farmer to consult their local Krishi Vigyan Kendra (KVK).
