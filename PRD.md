# Lenny Growth Assistant — Product Requirements Document

## 1. Product Overview

The **Lenny Growth Assistant** is an intelligent conversational application designed to synthesize and deliver actionable product and growth expertise sourced from *Lenny's Podcast* and newsletter transcripts. It combines general-purpose assistant capabilities with a Retrieval-Augmented Generation (RAG) engine grounded in verified transcript data from leading product and growth experts.

The assistant empowers users to ask nuanced growth questions, maintain multi-turn follow-up conversations, explore expert attribution cards, and generate persistent **Markdown documents** and **interactive HTML components** in a sandboxed preview environment.

---

## 2. Problem Statement

Product managers, growth practitioners, and founders face a overwhelming volume of fragmented podcasts, transcripts, and growth advice. When tackling specific operational challenges—such as designing cancellation flows, optimizing early retention, or defining core action metrics—practitioners spend hours skimming videos and articles to find reliable insights.

Existing LLM tools often hallucinate statistics or attribute advice incorrectly. Users need a centralized assistant that:
1. Instantly retrieves expert insights grounded in transcript evidence.
2. Clearly attributes claims to specific experts and episodes.
3. Preserves multi-turn conversation context for iterative refinement.
4. Synthesizes broad topics across multiple experts without single-source bias.
5. Transforms insights into ready-to-use artifacts like playbooks or UI components.

---

## 3. Target Users

- **Product Managers (PMs)**: Looking for actionable frameworks, metrics, and case studies to guide roadmap decisions.
- **Growth Leaders & Marketers**: Seeking strategies on user onboarding, retention, acquisition loops, and pricing.
- **Startup Founders & Co-founders**: Seeking advice on product-market fit, early traction, and team organizational design.
- **Product Leaders (VPs, CPOs)**: Comparing strategic perspectives across multiple industry leaders.
- **Students & Aspiring PMs**: Learning product management best practices directly from transcripts.

---

## 4. Goals

- **Natural Conversational Interface**: Provide a ChatGPT-style UI for chat, query input, and response formatting.
- **Grounded Transcript Knowledge**: Answer Lenny-specific growth questions using strict transcript evidence from PostgreSQL + `pgvector`.
- **Transparent Attribution**: Return source citations (guest name, episode title, transcript chunk index) for every substantive claim.
- **Multi-Turn Context Resolution**: Support follow-up questions (e.g. *"Explain that in simple terms"*) using session-bound message memory.
- **General Assistant Capabilities**: Handle greetings and general capability queries fast (<50ms) without invoking vector search.
- **Multi-Provider LLM Abstraction**: Support local Ollama (`llama3.2:1b`) alongside cloud providers (OpenAI, Anthropic) with seamless UI switching.
- **Cloud-to-Local Fallback**: Automatically fall back to local Ollama execution if cloud API credentials are unavailable.
- **Artifact Generation & Sandboxed Viewing**: Generate Markdown guides and self-contained HTML dashboards rendered safely inside a sandboxed iframe.
- **Seamless Local Experience**: Provide a simple Docker Compose setup that runs out of the box without requiring paid cloud API keys.

---

## 5. Non-Goals

- **Replacing Human Judgment**: The assistant provides structured recommendations and evidence, not autonomous product decisions.
- **100% Guaranteed Absolute Truth**: While answers are strictly grounded in transcript context, advice represents guest perspectives rather than objective physical laws.
- **Real-Time Web Search**: The system operates on indexed transcript knowledge, not external web searches.
- **Private Corporate Data Ingestion**: The system processes curated public transcripts, not private enterprise databases.
- **Autonomous Action Execution**: The assistant does not modify external tools or execute third-party API mutations.

---

## 6. Core User Journeys

### Journey 1 — Lenny Knowledge Question
1. **Input**: User asks, *"What is Patrick Campbell's advice on cancellation flows?"*
2. **Intent Routing**: Query is routed to the RAG pipeline.
3. **Retrieval**: Semantic vector search retrieves Patrick Campbell's transcript chunks from PostgreSQL.
4. **Generation & Grounding**: LLM synthesizes a concise, 3–5 sentence grounded answer.
5. **Output**: UI renders the answer along with expandable source attribution cards (guest, title, chunk index).

### Journey 2 — General Assistant / Fast-Path Question
1. **Input**: User asks, *"hii"* or *"what can you do?"*
2. **Intent Routing**: Fast-path detection identifies pure greetings or capability queries.
3. **Execution**: System returns a pre-configured response instantly (<50ms) without vector embedding or LLM calls.
4. **Output**: Friendly greeting or capability overview rendered with empty sources list.

### Journey 3 — Follow-Up Discussion
1. **Turn 1**: User asks, *"What does Sarah Tavel say about retention?"*
2. **System**: Answers with Sarah Tavel's principles on early user experience and cohort retention.
3. **Turn 2**: User asks, *"Explain that in 3 simple bullets."*
4. **Execution**: System loads the session's message history, resolves pronoun references ("that"), and formats the preceding retention concepts into 3 bullet points.

### Journey 4 — Artifact Creation
1. **Input**: User clicks "Create Artifact" or prompts, *"Create a retention playbook based on this discussion."*
2. **Generation**: Backend generates a structured document (`format: "markdown"` or `"html"`).
3. **Display**: Frontend opens the Artifact Viewer overlay displaying live rendered content alongside a "Code" tab.
4. **Action**: User copies raw markdown/HTML or downloads the file directly to their machine.

### Journey 5 — Provider Switching
1. **Action**: User selects **OpenAI** or **Anthropic** from the header dropdown menu.
2. **Request**: Subsequent chat requests send `provider: "openai"` or `provider: "anthropic"`.
3. **Fallback Handling**: If cloud credentials are not present in `.env`, backend catches the error and executes using local Ollama.

---

## 7. Functional Requirements

| ID | Requirement | Status |
| :--- | :--- | :--- |
| **FR-1** | **Conversational Chat**: Interactive interface supporting real-time chat requests and responses. | Implemented |
| **FR-2** | **Session Isolation**: Independent `session_id` management preventing context leakage between chats. | Implemented |
| **FR-3** | **General Assistant Routing**: Fast-path intent routing for greetings and meta-capability queries. | Implemented |
| **FR-4** | **Lenny Transcript RAG**: Question-answering pipeline backed by original podcast/newsletter transcripts. | Implemented |
| **FR-5** | **Semantic Retrieval**: Vector distance search powered by PostgreSQL and `pgvector`. | Implemented |
| **FR-6** | **Source Attribution**: Response payloads return guest name, episode title, URL, and chunk index. | Implemented |
| **FR-7** | **Grounded Fallback**: Returns explicit fallback message when retrieved evidence is insufficient. | Implemented |
| **FR-8** | **Follow-up Context**: History-aware query processing preserving conversation context across turns. | Implemented |
| **FR-9** | **Provider Abstraction**: Unified interface supporting Ollama, OpenAI, and Anthropic backends. | Implemented |
| **FR-10** | **Ollama Local Execution**: Default execution mode using local `llama3.2:1b` model. | Implemented |
| **FR-11** | **Cloud Providers**: Support for OpenAI (`gpt-4o-mini`) and Anthropic (`claude-3-5-haiku`). | Implemented |
| **FR-12** | **Cloud Fallback**: Automatic fallback to Ollama when cloud provider keys are missing or invalid. | Implemented |
| **FR-13** | **Markdown Artifacts**: Artifact generation delivering structured Markdown documents. | Implemented |
| **FR-14** | **HTML Artifacts**: Artifact generation delivering self-contained HTML/CSS code components. | Implemented |
| **FR-15** | **Artifact Viewer**: Dual-view overlay panel with live HTML iframe preview and code copying. | Implemented |
| **FR-16** | **API Validation**: Pydantic input validation returning HTTP 400/422 on invalid requests. | Implemented |
| **FR-17** | **Health Endpoints**: `/health` endpoint reporting server status and database connectivity. | Implemented |

---

## 8. Non-Functional Requirements

- **Reliability & Grounding**: Strict prompt constraints prevent hallucinations; answers are restricted to provided transcript chunks.
- **Security**: Cloud API keys are stored exclusively in root `.env` files; generated HTML is rendered inside a sandboxed `<iframe>` (`sandbox="allow-scripts"`).
- **Performance & Latency**: Fast-path responses resolve in <50ms. RAG retrieval completes in <400ms. Local CPU Ollama generation completes in ~8–15s per turn.
- **Maintainability**: Modular architecture separating FastAPI endpoints ([`main.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/main.py)), RAG logic ([`rag.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/rag.py)), LLM providers ([`llm_provider.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/llm_provider.py)), and database models ([`models.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/models.py)).
- **Local Developer Experience**: Single command Docker setup (`docker compose up -d`) running on host port 5433 to avoid port collisions.
- **Responsive UI**: Modern React frontend with dark sidebar, soft violet accents, auto-scrolling message list, and responsive layout.

---

## 9. AI / RAG Requirements

- **Ingestion & Chunking**: Transcripts are processed into overlapping semantic text passages.
- **Embeddings**: 768-dimensional vector representations generated via `nomic-embed-text`.
- **Vector Indexing**: Stored in PostgreSQL using `pgvector` IVFFlat/HNSW indexes.
- **Evidence Selection & Diversification**: `diversify_sources()` selects up to 3–5 distinct transcript chunks while capping repeated episodes.
- **Grounding Validation**: Post-generation validator verifies expert name alignment, token overlap, and sentence completeness.
- **Insufficient-Evidence Fallback**: Returns exact fallback string: *"I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."* when context is missing.

---

## 10. Artifact Requirements

- **Markdown Documents**: Clean headers (`#`, `##`), bullet lists, and bold callouts. Outer code fences are stripped automatically.
- **HTML Components**: Self-contained single-file HTML/CSS components with dark mode containers (`#0f172a`).
- **Sandboxed Rendering**: Rendered inside `<iframe sandbox="allow-scripts">` to isolate CSS/JS scope.
- **Export Utility**: One-click "Copy Code" button and file download trigger.

---

## 11. LLM Provider Requirements

- **Provider Interface**: `query_llm(messages, temperature, provider)` routes requests dynamically.
- **Local Demo Support**: Default provider is `ollama` with `llama3.2:1b`. No external API keys required for testing.
- **Cloud Integration**: Support for OpenAI (`gpt-4o-mini`) and Anthropic (`claude-3-5-haiku`).
- **Resilience**: Catches cloud HTTP errors or missing API keys, logging a warning and falling back seamlessly to Ollama.

---

## 12. Success Metrics

| Metric | Metric Type | Target Goal | Status / Verification |
| :--- | :--- | :--- | :--- |
| **Lenny Source Relevance** | Target Metric | > 90% of transcript queries return valid sources | Verified via RAG tests |
| **Grounded Answer Rate** | Target Metric | > 95% of claims directly supported by evidence | Enforced by grounding validator |
| **Follow-up Context Resolution** | Target Metric | > 90% accuracy resolving pronouns across turns | Verified via multi-turn tests |
| **Artifact Generation Success** | Target Metric | 100% valid Markdown & standalone HTML | Verified via artifact tests |
| **API Test Suite Pass Rate** | Measured Metric | 100% (18/18 passing tests) | Verified (`python -m unittest`) |
| **Provider Fallback Success** | Measured Metric | 100% clean fallback to Ollama | Verified (`test_llm_provider.py`) |

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Hallucination / False Claims** | High | Grounding validator checks answer token overlap against retrieved context. |
| **Single-Source Dominance** | Medium | `diversify_sources()` caps max chunks per episode to ensure multi-expert synthesis. |
| **Local LLM Latency (CPU)** | Medium | Response word targets capped; model prefill optimized with `num_predict=96`. |
| **Cloud API Rate Limits / Key Absence** | Low | Provider abstraction catches exceptions and falls back cleanly to local Ollama. |
| **Malicious HTML Artifacts** | High | Preview rendered inside sandboxed `<iframe>` (`sandbox="allow-scripts"`). |
| **API Key Leakage** | High | Credentials restricted to uncommitted `.env` files. |

---

## 14. Future Improvements (Roadmap)

> *Note: The items below represent potential future enhancements and are not currently implemented.*

- **Streaming Responses**: Server-Sent Events (SSE) streaming for real-time token rendering.
- **Multi-Session Visual History**: Persistent conversation session sidebar with title auto-summarization.
- **Expanded Embedding Benchmarks**: Evaluating alternative embedding models (`text-embedding-3-small`, `bge-large`).
- **Advanced RERANKING**: Hybrid sparse-dense reranking using Cross-Encoders.
- **Production Observability**: Integrated OpenTelemetry and LangSmith tracing for latency monitoring.

---

## 15. Acceptance Criteria

The product release is considered complete based on the following verified criteria:

1. **Independent Session Execution**: Multiple distinct `session_id`s maintain separate conversation contexts.
2. **Grounded Answers with Sources**: Transcript queries return direct answers accompanied by guest and episode metadata.
3. **Fast-Path Greetings**: Pure greetings and capability queries return in <50ms without vector search.
4. **Follow-Up Handling**: Sequential questions in the same session correctly inherit topic context.
5. **Provider Flexibility**: Switching providers via UI payload correctly updates the LLM engine.
6. **Local Out-of-the-Box Demo**: System runs locally using Ollama without requiring cloud API keys.
7. **Artifact Generation & Preview**: Markdown and HTML artifacts generate cleanly and preview in the sandboxed viewer.
8. **Automated Test Suite**: All 18 backend unit tests pass without error (`python -m unittest discover -s tests -v`).
