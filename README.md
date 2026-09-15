# Lenny Growth Assistant

## 1. Overview

The **Lenny Growth Assistant** is a full-stack, AI-powered product and growth intelligence application built upon transcripts from *Lenny's Podcast* and newsletters. Designed for product managers, growth leaders, founders, and engineers, it provides an interactive conversational workspace that answers complex product and growth queries using grounded expert advice from industry leaders.

The application seamlessly pairs general-purpose conversational capabilities with a specialized Retrieval-Augmented Generation (RAG) system. Users can ask broad or expert-specific growth questions, maintain multi-turn follow-up discussions, and generate persistent, high-value **Markdown documentation** or **standalone HTML UI components/dashboards** directly rendered within a secure, sandboxed artifact viewer.

---

## 2. Key Features

- **ChatGPT-Style Conversational UI**: Polished, minimal visual design with smooth auto-scroll, formatted message rendering, and responsive sidebar navigation.
- **General-Purpose Assistant & Fast Paths**: Instant fast-path responses for pure greetings and capability/meta queries (<50ms) without unnecessary vector database or LLM calls.
- **Lenny Transcript RAG**: Strict, evidence-backed answer generation grounded exclusively in original transcript content.
- **Semantic Retrieval**: Fast vector distance search powered by PostgreSQL and `pgvector`.
- **Expert & Source Attribution**: Every grounded claim returns clear source cards featuring the guest name, episode title, and transcript chunk index.
- **Multi-Turn Session Context**: Session-isolated conversation memory allowing seamless follow-up references (e.g. "what else did she say?").
- **Local Ollama LLM**: Default zero-cost local execution using `llama3.2:1b` (no external API keys needed for evaluation).
- **OpenAI & Anthropic Cloud Providers**: Support for cloud models (`gpt-4o-mini`, `claude-3-5-haiku`) with seamless UI provider selection.
- **Graceful Cloud $\rightarrow$ Ollama Fallback**: Automatic fallback to local Ollama if cloud API keys are missing or rate-limited.
- **Markdown Artifact Generation**: One-click generation of structured guides, playbooks, and strategies formatted with clean Markdown headings.
- **HTML Artifact Generation**: Standalone HTML/CSS code generation for modern interactive cards and dashboards.
- **Sandboxed HTML Artifact Viewer**: Safe previewing of generated HTML components inside a sandboxed iframe (`sandbox="allow-scripts"`).
- **PostgreSQL + pgvector**: Vector database schema storing 768-dimensional embeddings alongside chunk metadata.
- **Health & API Endpoints**: Endpoints for server status, database health checks, chat completion, and artifact generation.

---

## 3. Architecture

```text
                                  +-------------------+
                                  |   React Frontend  |
                                  +---------+---------+
                                            |
                                            v (HTTP POST)
                                  +---------+---------+
                                  |   FastAPI Backend |
                                  +---------+---------+
                                            |
                                            v
                                  +---------+---------+
                                  |   Intent Router   |
                                  +----+----+----+----+
                                       |    |    |
            +--------------------------+    |    +--------------------------+
            |                               v                               |
            v                       +-------+-------+                       v
+-----------+-----------+           |  Lenny RAG    |           +-----------+-----------+
| Greeting / Capability |           +-------+-------+           |  Follow-up Context    |
|       Fast Path       |                   |                   |       Resolver        |
+-----------+-----------+                   v                   +-----------+-----------+
            |                     +---------+---------+                     |
            +-------------------->|  LLM Abstraction  |<--------------------+
                                  +----+----+----+----+
                                       |    |    |
                           +-----------+    |    +-----------+
                           v                v                v
                     +-----+-----+    +-----+-----+    +-----+-----+
                     |  Ollama   |    |  OpenAI   |    | Anthropic |
                     | (Local)   |    | (Cloud)   |    | (Cloud)   |
                     +-----------+    +-----------+    +-----------+
```

### Lenny RAG Pipeline

```text
Lenny Transcripts (JSON) ──> Text Chunking ──> nomic-embed-text (768d) ──> PostgreSQL + pgvector
                                                                                   │
User Query ──────────────────> Embedding Search ───────────────────────────────────┘
                                       │
                                       v
                           Diversified Evidence Chunks
                                       │
                                       v
                         Grounded LLM Prompt Context
                                       │
                                       v
                            Answer + Source Citations
```

---

## 4. Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 19 / Vite 6 / TailwindCSS 4 / Lucide React |
| **Backend** | FastAPI / Python 3.11+ / SQLAlchemy / Pydantic |
| **Database** | PostgreSQL 16 / pgvector (`pgvector/pgvector:pg16`) |
| **Local LLM** | Ollama / `llama3.2:1b` |
| **Embeddings** | Ollama / `nomic-embed-text` (768 dimensions) |
| **Cloud LLMs** | OpenAI (`gpt-4o-mini`) / Anthropic (`claude-3-5-haiku`) |
| **Testing** | Python `unittest` / FastAPI `TestClient` |
| **Containerization** | Docker Compose |

---

## 5. Project Structure

```text
lenny-growth-assistant/
├── README.md                  # Project documentation
├── docker-compose.yml         # PostgreSQL + pgvector database service
├── .env.example               # Safe environment variable configuration template
├── backend/
│   ├── main.py                # FastAPI application & REST endpoints
│   ├── rag.py                 # RAG pipeline, prompt generation & grounding validator
│   ├── search.py              # Semantic vector search & PostgreSQL pgvector queries
│   ├── llm_provider.py        # LLM abstraction (Ollama, OpenAI, Anthropic + fallback)
│   ├── database.py            # SQLAlchemy database connection engine
│   ├── models.py              # Database models (TranscriptChunk, ChatSession, ChatMessage)
│   ├── loader.py              # Transcript JSON loader & ingestion script
│   ├── chunker.py             # Overlapping text chunker utility
│   ├── embedder.py            # Vector embedding generator (nomic-embed-text)
│   └── skills/
│       └── ship30.py          # Ship30 writing framework skill implementation
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main ChatGPT-style chat interface & artifact viewer
│   │   ├── index.css          # Styling & theme variables
│   │   └── main.jsx           # React entry point
│   ├── package.json           # Frontend dependencies (React, Tailwind, Lucide)
│   └── vite.config.js         # Vite configuration
└── tests/
    ├── test_api.py            # Endpoints, chat, artifacts, and RAG integration tests
    └── test_llm_provider.py   # LLM provider abstraction & fallback unit tests
```

---

## 6. Prerequisites

Ensure you have the following installed on your host system:

- **Python 3.11+**
- **Node.js 18+ & npm**
- **Docker Desktop** (with Docker Compose enabled)
- **Ollama** (running locally)

### Required Ollama Models

Before launching the backend, pull the local generation model and embedding model via terminal:

```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

> **Note**: The local Ollama setup is completely self-contained and sufficient for evaluating the entire application without needing cloud API keys.

---

## 7. Environment Configuration

Copy the example environment file to `.env` in the root directory:

```bash
cp .env.example .env
```

### Safe Environment Example (`.env`)

```ini
# Database Configuration (Port 5433 mapped via Docker Compose)
DATABASE_URL=postgresql+psycopg://lenny:lenny_password@localhost:5433/lenny_db

# Primary LLM Provider (ollama [default], openai, anthropic)
LLM_PROVIDER=ollama
CHAT_MODEL=llama3.2:1b

# Optional Cloud Provider Keys (leave empty to use local Ollama fallback)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-haiku-20241022
```

> ⚠️ **IMPORTANT**: Never commit `.env` containing real secrets or API keys to git repositories. `.env` is listed in `.gitignore`.

---

## 8. Running Locally

Execute the following commands from the project root (`lenny-growth-assistant`):

### Terminal 1: Database Service (Docker)
```powershell
docker compose up -d
```
*Note: PostgreSQL is exposed on host port **5433** to prevent conflicts with any pre-existing PostgreSQL instances on port 5432.*

### Terminal 2: Backend API (FastAPI)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```
The API server will start at `http://localhost:8000`.

### Terminal 3: Frontend Web App (Vite + React)
```powershell
cd frontend
npm run dev
```
Open your browser and navigate to: **[http://localhost:5173](http://localhost:5173)**

---

## 9. LLM Provider Configuration

The backend features a unified LLM Provider Abstraction [`llm_provider.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/llm_provider.py) supporting three engines:

1. **Ollama (Local / Default)**:
   - Zero configuration required.
   - Runs locally on model `llama3.2:1b`.
   - Requires no cloud credentials or internet connection.
2. **OpenAI (Cloud)**:
   - Uses `gpt-4o-mini`.
   - Requires `OPENAI_API_KEY` set in `.env`.
3. **Anthropic (Cloud)**:
   - Uses `claude-3-5-haiku-20241022`.
   - Requires `ANTHROPIC_API_KEY` set in `.env`.

### Provider Switching & Automatic Fallback
Users can switch between **Ollama**, **OpenAI**, and **Anthropic** dynamically using the dropdown selector in the header of the frontend UI. If a cloud provider is selected but its API key is missing, empty, or fails, the provider abstraction gracefully catches the error and falls back to local Ollama execution.

---

## 10. Knowledge Base / RAG

- **Data Source**: Original transcripts from *Lenny's Podcast* and newsletter archive.
- **Chunking**: Transcripts are split into semantic chunks with overlapping context boundaries.
- **Embeddings**: Vector embeddings generated using `nomic-embed-text` (768 dimensions).
- **Storage**: Stored in PostgreSQL using the `pgvector` extension for fast cosine distance vector indexing.
- **Evidence Diversification**: Search results are passed through `diversify_sources()` to prevent single-episode dominance and synthesize answers across diverse experts (e.g., Sarah Tavel, Patrick Campbell, Dan Hockenmaier).
- **Pre-populated Database**: The submitted demo database container comes pre-seeded with indexed transcript embeddings ready for instant querying.

---

## 11. Conversation & Session Model

- **Session Isolation**: Every user chat session generates a unique `session_id`.
- **Context Continuity**: Message history within a session is stored in PostgreSQL (`ChatSession` and `ChatMessage` models), allowing follow-up queries (e.g., *"What did he say about cancellation flows?"*) to resolve pronouns against preceding turns.
- **Session Privacy**: New sessions maintain complete context isolation and do not leak context from previous conversations.

---

## 12. Artifact Generation

Users can request formatted artifacts (playbooks, strategy guides, dashboards) directly within chat.

- **Formats**: Supports `markdown` and `html`.
- **Artifact Viewer**: Displays generated artifacts in an overlay panel with side-by-side tabs for live preview and raw code.
- **Sandboxed Execution**: Generated HTML content is rendered inside an isolated `<iframe>` with `sandbox="allow-scripts"` to protect against untrusted script execution.
- **Exporting**: One-click **Copy Code** and **Download File** functionality.

---

## 13. Ship30 Skill

The assistant integrates a specialized **Ship30 Writing Skill** ([`backend/skills/ship30.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/skills/ship30.py)) following 30-for-30 content creation principles:

- **Strong Hooks**: Grabs attention with direct, high-leverage opening lines.
- **Narrative Progression**: Logical structure that guides readers from problem to solution.
- **High Skimmability**: Clear subheadings, bold highlights, and formatted bullet lists.
- **Specificity & Actionability**: Concrete tactics, metrics, and step-by-step guidance.
- **Strict Grounding**: Factual assertions are tied directly to verified transcript evidence.

---

## 14. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root endpoint returning server status. |
| `GET` | `/health` | Health check verifying database connection status. |
| `POST` | `/api/chat` | Main chat endpoint executing intent routing, RAG, and session persistence. |
| `POST` | `/api/artifacts` | Artifact generation endpoint producing Markdown or HTML documents. |

### Example Request (`POST /api/chat`)
```json
{
  "session_id": "session_demo_101",
  "message": "What does Sarah Tavel say about retention?",
  "provider": "ollama"
}
```

### Example Response (`POST /api/chat`)
```json
{
  "session_id": "session_demo_101",
  "message": "Sarah Tavel emphasizes that retention is the single best indicator of product-market fit...",
  "sources": [
    {
      "guest": "Sarah Tavel",
      "title": "Hierarchy of Engagement",
      "url": "https://www.lennyspodcast.com/sarah-tavel",
      "chunk_index": 4
    }
  ],
  "provider": "ollama"
}
```

---

## 15. Testing

The backend includes a comprehensive automated test suite covering API contracts, input validation, session isolation, grounding, fast paths, provider abstraction, and cloud fallback.

### Run Unit Tests
```powershell
backend\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Verified Passing Test Suite (18 Tests)
- `test_root_endpoint`: **OK**
- `test_health_endpoint`: **OK**
- `test_successful_chat_request`: **OK**
- `test_invalid_empty_message_validation`: **OK**
- `test_invalid_empty_session_id_validation`: **OK**
- `test_session_isolation`: **OK**
- `test_capability_fast_path`: **OK**
- `test_broad_retention_question_synthesis`: **OK**
- `test_multiturn_sequential_retention_session`: **OK**
- `test_markdown_artifact_response`: **OK**
- `test_html_artifact_response`: **OK**
- `test_artifact_empty_prompt_validation`: **OK**
- `test_artifact_invalid_format_validation`: **OK**
- `test_default_ollama_provider`: **OK**
- `test_openai_api_call_with_key`: **OK**
- `test_openai_fallback_without_key`: **OK**
- `test_anthropic_api_call_with_key`: **OK**
- `test_anthropic_fallback_without_key`: **OK**

---

## 16. Error Handling & Resilience

- **Missing Cloud API Keys**: Fallback to local Ollama model if OpenAI/Anthropic credentials are absent.
- **Ollama Service Outage**: Returns explicit HTTP 503 status code with clean error payload.
- **Validation Errors**: Pydantic schema validation returns HTTP 400/422 for empty or malformed requests.
- **Empty Retrieval**: Triggers a clean fallback message (*"I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."*) rather than hallucinating answers.
- **Truncated Model Generation**: Post-processing guarantees every returned response ends cleanly on a completed sentence.

---

## 17. Security

- **Environment Isolation**: Sensitive configuration values and API keys are loaded via environment variables.
- **Sandboxed Rendering**: Rendered HTML artifacts run inside sandboxed iframes preventing DOM manipulation or cookie access.
- **Sanitized Logging**: Request diagnostics log prompt sizes and performance timings without leaking credentials or secret keys.

---

## 18. Recommended Demo Flow

1. **Launch App**: Open `http://localhost:5173`.
2. **Greeting Fast-Path**: Type `"hii"` $\rightarrow$ Receive an instant greeting (<50ms).
3. **Capability Fast-Path**: Type `"What can you do?"` $\rightarrow$ Receive application overview without vector search overhead.
4. **Lenny-Specific Query**: Type `"What is Patrick Campbell's advice on cancellation flows?"` $\rightarrow$ Review grounded response with guest and episode citations.
5. **Follow-Up Query**: Type `"How should product teams improve retention?"` $\rightarrow$ Observe multi-expert synthesis across Sarah Tavel, Patrick Campbell, and Dan Hockenmaier.
6. **Provider Switching**: Toggle provider dropdown to **OpenAI** or **Anthropic** (observe fallback behavior if no key is configured).
7. **Markdown Artifact**: Click `"Create Artifact"` or prompt `"Create a retention playbook"` (Markdown format) $\rightarrow$ Inspect formatted document.
8. **HTML Artifact**: Prompt `"Create an HTML retention dashboard component"` $\rightarrow$ Inspect live rendering in the sandboxed previewer.

---

## 19. Known Limitations

- **Local CPU Ollama Latency**: When running locally without GPU acceleration, `llama3.2:1b` prompt prefill and generation may take 8–15 seconds per turn. Using cloud providers (OpenAI / Anthropic) significantly accelerates response times.

---

## 20. Evaluation & Submission Notes

- **Backend Logic**: Implemented in [`backend/rag.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/rag.py), [`backend/main.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/main.py), and [`backend/llm_provider.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/llm_provider.py).
- **Frontend App**: Implemented in [`frontend/src/App.jsx`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/frontend/src/App.jsx).
- **Automated Tests**: Located in [`tests/test_api.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/tests/test_api.py) and [`tests/test_llm_provider.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/tests/test_llm_provider.py).
- **Database Model & Docker**: Configured in [`docker-compose.yml`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/docker-compose.yml) and [`backend/models.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/models.py).
