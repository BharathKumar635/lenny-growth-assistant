# Design — Lenny Growth Assistant

## 1. Design Overview

The **Lenny Growth Assistant** is designed as a clean, modern, ChatGPT-inspired conversational workspace tailored for product and growth intelligence. It balances a familiar chat UI with specialized Retrieval-Augmented Generation (RAG) capabilities grounded in transcripts from *Lenny's Podcast* and newsletter archive.

### Core Design Philosophy:
- **Familiar & Accessible**: Uses standard chat interaction patterns (auto-scrolling messages, sidebar navigation, clear input composer).
- **Trust & Transparency**: Displays explicit source attribution cards for every grounded claim, allowing users to verify guest names, episode titles, and transcript chunk indices.
- **Fast & Responsive**: Implements deterministic fast paths (<50ms) for greetings and meta-capability queries.
- **Artifact-Centric Productivity**: Provides a split-screen workspace panel for generating, inspecting, copying, and downloading Markdown guides or interactive HTML dashboards.
- **Local-First & Multi-Provider**: Built to run zero-cost local LLM inference via Ollama (`llama3.2:1b`) out of the box, with optional UI switching and fallback for cloud providers (OpenAI, Anthropic).

---

## 2. User Experience Design

The single-page application ([`frontend/src/App.jsx`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/frontend/src/App.jsx)) provides a split-view interactive layout:

```text
+---------------------------------------------------------------------------------------------+
| Header: Lenny Growth Assistant  | Provider: [Ollama (Local) v]  | [Create Artifact] | Sidebar |
+-------------------------------+-----------------------------------------------+-------------+
| Left Sidebar (Collapsible)   | Main Chat Workspace                           | Artifact    |
| - New Chat (+)                |                                               | Panel       |
| - Session History List        | User: "What is Patrick Campbell's advice...?" | (Split View)|
| - Quick Actions               |                                               |             |
|                               | Assistant: "Patrick Campbell recommends..."   | - Live      |
|                               |   [v] Sources (1 Source)                      |   Preview   |
|                               |       • Patrick Campbell | Cancellation Flows | - Raw Code  |
|                               |                                               | - Copy      |
|                               | +-------------------------------------------+ | - Download  |
|                               | | Input composer...                [ Send ] | |             |
|                               | +-------------------------------------------+ |             |
+-------------------------------+-----------------------------------------------+-------------+
```

### Key UI Subsystems:
- **Application Layout**: Fixed-height viewport layout with collapsible left sidebar, center main chat feed, and dynamic right-side artifact panel.
- **Header & Provider Selector**: Displays status indicators, app title, and a dropdown selector allowing live provider switching between `Ollama (Local)`, `OpenAI (Cloud)`, and `Anthropic (Cloud)`.
- **Collapsible Sidebar**: Lists active chat sessions saved in `localStorage`, a `+ New Chat` button, and quick-start prompt triggers.
- **Welcome & Empty State**: When starting a fresh session, displays an hero card with feature highlights and 4 clickable sample prompts (*"How can I improve product retention?"*, *"What does Patrick Campbell say about cancellation flows?"*, etc.).
- **Message List**: Renders user and assistant message bubbles. Assistant messages format paragraphs, bold text, and bullet lists cleanly using the `FormattedText` component.
- **Expandable Source Cards**: Accordion-style source widgets beneath assistant messages displaying guest name, episode title, and chunk index.
- **Input Composer**: Multi-line auto-resizing textarea with keyboard `Enter` submission and a styled `Send` button.
- **Artifact Workspace Panel**: Sliding split-screen panel displaying generated Markdown or HTML code alongside a live preview.

---

## 3. Visual Design System

The application uses TailwindCSS 4 with a curated palette featuring subtle violet accents on a clean light-mode neutral background.

### Design Tokens & Visual Hierarchy:
- **Color Palette**:
  - **Primary Accent**: Violet (`bg-violet-600`, `text-violet-600`, `border-violet-200`)
  - **Main Background**: Off-white / light slate (`bg-slate-50`)
  - **Card Containers**: Pure white (`bg-white`) with subtle borders (`border-slate-200`)
  - **Text Typography**: Charcoal (`text-slate-900`) for headings, dark slate (`text-slate-800`) for body text, muted slate (`text-slate-500`) for secondary metadata.
- **Typography**: Clean sans-serif system font stack with high legibility, strict vertical rhythm, and line-height spacing (`leading-relaxed`).
- **Cards & Elevation**: Rounded container corners (`rounded-xl`, `rounded-2xl`) paired with soft drop shadows (`shadow-xs`, `shadow-sm`, `shadow-xl`).
- **Icons & Avatars**: Lucide React icons (`MessageSquare`, `Sparkles`, `BookOpen`, `Code`, `FileText`, `Copy`, `Download`, `CheckCircle2`). User messages use a slate user icon; assistant responses use a violet bot icon.
- **Hover & Focus States**: Subtle background transitions (`hover:bg-slate-100`, `hover:bg-violet-700`) and focus ring highlights (`focus:ring-2 focus:ring-violet-500`).

---

## 4. Conversation Design

### User Interaction Flows:

1. **Starting a New Session**: Clicking `+ New Chat` generates a fresh UUID session identifier (`generateSessionId()`), resets chat message state, and clears active errors.
2. **Asking a Lenny Knowledge Query**:
   - User types: *"What is Patrick Campbell's advice on cancellation flows?"*
   - UI displays user bubble and loading spinner.
   - Assistant returns grounded 3–5 sentence answer with source card accordion (*"Patrick Campbell | Cancellation Flows"*).
3. **Asking a General or Fast-Path Query**:
   - User types: *"hii"* or *"what can you do?"*
   - Backend fast path triggers <50ms response without vector retrieval.
   - UI renders instant response with empty sources.
4. **Asking a Follow-Up Query**:
   - User types: *"Explain that in simple terms."*
   - Backend loads session history to resolve *"that"*, returning a simplified breakdown of preceding concepts.
5. **Generating an Artifact**:
   - User clicks "Create Artifact" or prompts *"Create a retention playbook"*.
   - Backend calls `/api/artifacts`, opening the right-side Artifact Panel with live preview and copy/download controls.
6. **Switching LLM Providers**:
   - User switches header dropdown to **OpenAI** or **Anthropic**.
   - Subsequent chat API calls pass `"provider": "openai"`. If no cloud key is set in `.env`, system gracefully falls back to Ollama.

---

## 5. Information Architecture

Information is organized into 3 primary visual zones:

1. **Left Navigation Zone (Sidebar)**:
   - Primary action: `+ New Chat`.
   - History list: Saved chat sessions with session ID and relative timestamps.
   - Quick prompts: Preset growth questions for immediate exploration.
2. **Center Primary Conversation Zone (Main Feed)**:
   - Header bar with provider controls.
   - Chronological message history.
   - Direct inline source attribution cards attached to specific assistant turns.
   - Bottom floating input composer.
3. **Right Workspace Zone (Artifact Panel)**:
   - Artifact header: Title, format tag (`MARKDOWN` or `HTML`), artifact ID.
   - Action buttons: `Copy Code` and `Download File`.
   - Content body: Sandboxed live HTML iframe or formatted Markdown text.

---

## 6. RAG / Answer Design

The answer experience is engineered around verifiable, trustworthy retrieval:

- **Semantic Retrieval**: Queries are embedded into 768-dimensional vectors (`nomic-embed-text`) and matched against PostgreSQL `pgvector` indexes.
- **Evidence Diversification**: `diversify_sources()` restricts candidates to 1 chunk per episode, ensuring broad queries synthesize insights across multiple distinct experts (e.g., Sarah Tavel, Patrick Campbell, Dan Hockenmaier).
- **Expert Attribution**: Prompts strictly instruct the model to attribute claims to specific experts.
- **Grounding Validation**: Post-generation validator verifies token overlap and expert name alignment.
- **Fallback Answer**: If evidence is missing, returns exact fallback text: *"I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."*

---

## 7. Session / Multi-Turn UX

- **Independent Session Isolation**: Every conversation maintains a unique `session_id`.
- **History Memory**: Session history records are stored in PostgreSQL (`chat_sessions` and `chat_messages` tables). Up to 6 recent turns are passed into LLM prompt context.
- **Pronoun Resolution**: Follow-up questions (*"What else did she say?"*) correctly resolve pronouns against previous messages in the session.
- **Evidence Isolation**: Conversation history is strictly used for reference resolution; previous assistant answers are explicitly banned from acting as factual evidence.

---

## 8. Artifact UX

- **Creation Trigger**: Triggered via `POST /api/artifacts` endpoint.
- **Supported Formats**: `markdown` and `html`.
- **Markdown Rendering**: Strips outer markdown code fences (` ```markdown `) and unescapes headers (`\##` $\rightarrow$ `##`). Renders structured headers, lists, and bold text.
- **HTML Sandboxed Preview**: Rendered using an isolated `<iframe>` with strict empty-string sandbox configuration:
  ```jsx
  <iframe
    sandbox=""
    srcDoc={artifact.content}
    title={artifact.title}
    className="w-full h-full min-h-[600px] border border-slate-200 rounded-xl bg-white shadow-xs"
  />
  ```
- **Security Guarantee**: The `sandbox=""` attribute completely restricts script execution, popups, and parent window DOM access, rendering untrusted generated HTML safely.

---

## 9. LLM Provider UX

- **Provider Selection**: Header dropdown offers `Ollama (Local)`, `OpenAI (Cloud)`, and `Anthropic (Cloud)`.
- **Local Default**: Default provider is `ollama` running `llama3.2:1b`. No external API keys are required for testing.
- **Cloud API Keys**: `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are read from root `.env`. Real secrets are never rendered in frontend UI or logs.
- **Automatic Fallback**: If a user selects OpenAI/Anthropic without a valid API key, the system logs a backend warning and falls back to Ollama without failing the request.

---

## 10. Backend/API Design

The API interface is defined in [`backend/main.py`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/backend/main.py):

| Method | Route | Request Schema | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | None | `{message: str}` | API running status endpoint. |
| `GET` | `/health` | None | `{status: str, database: str}` | Health check for API and PostgreSQL DB. |
| `POST` | `/api/chat` | `ChatApiRequest` | `ChatApiResponse` | Executes intent routing, RAG search, LLM completion, and DB message persistence. |
| `POST` | `/api/artifacts` | `ArtifactApiRequest` | `ArtifactApiResponse` | Generates structured Markdown or HTML artifact documents. |

---

## 11. Component Design

### Frontend Architecture ([`frontend/src/App.jsx`](file:///c:/Users/bhara/Desktop/OOg/lenny-growth-assistant/frontend/src/App.jsx))
- **`App`**: Main stateful component managing session ID, message history, active errors, loading states, selected LLM provider, and artifact panel visibility.
- **`FormattedText`**: Text rendering component that converts raw LLM text into formatted React DOM paragraphs, bullet lists, and bold text without raw markdown tags.
- **`SourceCardAccordion`**: Collapsible widget displaying guest name, episode title, source URL, and chunk index.
- **`ArtifactViewerPanel`**: Split-screen overlay rendering generated Markdown or sandboxed HTML code with copy/download buttons.

### Backend Architecture (`backend/`)
- **`main.py`**: FastAPI route handlers and Pydantic validation schemas.
- **`rag.py`**: Intent router, fast paths, query analysis, source diversification, prompt construction, grounding validation, and artifact generation.
- **`search.py`**: Semantic vector search with `pgvector` cosine distance queries.
- **`llm_provider.py`**: Multi-provider LLM abstraction layer with automatic fallback logic.
- **`skills/ship30.py`**: Ship30 content creation framework skill.

---

## 12. State Management

The frontend relies on standard React hooks (`useState`, `useEffect`, `useRef`) without third-party state libraries (no Redux/Zustand):

- **Local Storage Persistence**: Active sessions list saved to `localStorage` under key `lenny_chat_sessions`.
- **Session State**: `sessionId` manages active conversation identifier.
- **Message List State**: `messages` array maintains turn history in memory for active render.
- **Provider State**: `llmProvider` stores selected provider string (`"ollama"`, `"openai"`, `"anthropic"`).
- **Artifact State**: `artifact` object stores active generated artifact payload (`title`, `format`, `content`, `artifact_id`).

---

## 13. Error and Empty States

- **Empty Chat State**: Displays welcome hero card with sample prompt buttons.
- **Loading Indicators**: Displays animated bouncing dot spinner during LLM generation.
- **Backend Service Error**: Displays prominent red alert banner (`AlertCircle`) with clean error description.
- **Missing API Key Fallback**: Silently falls back to local Ollama execution with backend logging; user query completes successfully.
- **Insufficient Evidence**: Displays grounded fallback message: *"I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."*

---

## 14. Accessibility and Usability

- **Keyboard Interaction**: Form submission triggered via `Enter` key (with `Shift+Enter` for multi-line newline).
- **Focus Indicators**: Interactive elements feature clear focus outlines (`focus:ring-2 focus:ring-violet-500`).
- **Contrast Ratios**: Dark charcoal text (`#0f172a`) on light background (`#f8fafc`) meets standard readability guidelines.
- **Auto-Scroll Behavior**: Chat feed automatically scrolls smooth to bottom (`messagesEndRef.current.scrollIntoView()`) upon receiving new messages.

---

## 15. Security-by-Design

- **Secrets Management**: Secrets loaded exclusively via `.env`; excluded from git tracking via `.gitignore`.
- **Strict iframe Sandboxing**: Rendered HTML artifacts use `sandbox=""` (empty string permissions), disabling script execution, popup creation, and parent window DOM access.
- **Input Validation**: Pydantic models validate input types, enforcing non-empty strings and format constraints (`markdown` or `html`).

---

## 16. Performance Design

- **Fast-Path Latency**: Greetings and capability queries resolve in <50ms without database or LLM invocation.
- **Vector Search Latency**: PostgreSQL `pgvector` distance queries execute in <400ms.
- **Context Capping**: Retrieved context capped at top 2–3 chunks (~1400 tokens) to prevent local Ollama prompt prefill bottlenecks.
- **Model Generation Tuning**: Ollama configured with `num_predict=96` and `keep_alive="5m"` to keep local model warm.

---

## 17. Design Trade-offs

- **ChatGPT UI vs Lenny Identity**: Combined familiar chat UI conventions with custom violet branding and transcript attribution cards to signal a specialized growth assistant.
- **Local vs Cloud Inference**: Prioritized local Ollama execution as default to enable zero-cost local evaluation, while providing cloud provider toggles for faster inference.
- **Small Evidence Context vs Large Context**: Restricted prompt context to 2–3 highly relevant chunks to eliminate hallucination and local CPU latency bottlenecks.
- **Sandboxed HTML vs Unrestricted Rendering**: Used strict empty-string iframe sandboxing (`sandbox=""`) to prioritize security over executing embedded JavaScript.

---

## 18. Known Limitations

- **Local CPU Ollama Latency**: Running local Ollama on CPU hardware takes 8–15 seconds per turn. Using cloud providers (OpenAI / Anthropic) resolves latency.
- **Single-Turn Artifact Generation**: Artifact generation currently generates documents based on the prompt and recent history, without streaming support.

---

## 19. Design Validation

The design and technical implementation have been validated through automated testing:

- **Automated Unit & Integration Test Suite**: 18 passing tests in `tests/test_api.py` and `tests/test_llm_provider.py` (`Ran 18 tests in 71.399s, OK`).
- **Validated Areas**: Fast-path greetings, capability routing, broad retention multi-expert synthesis, session isolation, provider abstraction, cloud API key fallback, and artifact generation.

---

## 20. Future Design Improvements

> *Note: The features below are not implemented in the current codebase.*

- **Server-Sent Events (SSE) Response Streaming**: Real-time token streaming for chat answers and artifacts.
- **Persistent Multi-Session History UI**: Sidebar listing previous chat sessions with title auto-summarization and session deletion.
- **Vector Reranking**: Advanced Cross-Encoder reranking for search candidates.
- **Production Observability**: Integrated LangSmith / OpenTelemetry tracing.

---

## 21. Final Design Summary

The Lenny Growth Assistant design establishes a modern, transparent, and resilient conversational product workspace. By pairing fast-path intent routing, PostgreSQL `pgvector` semantic retrieval, multi-expert source diversification, strict grounding validation, multi-provider fallbacks, and sandboxed artifact rendering, the system provides an exceptional user experience built on trust and technical excellence.
