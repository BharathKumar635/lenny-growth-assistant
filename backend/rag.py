import os
import re
import time
from llm_provider import query_llm
from search import search_similar_chunks


CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:1b")


SYSTEM_PROMPT = """You are Lenny's Growth Assistant.

Answer ONLY the CURRENT USER QUESTION using the RETRIEVED TRANSCRIPT EVIDENCE supplied below.

CRITICAL INSTRUCTIONS:
1. The CURRENT USER QUESTION is your highest-priority instruction. Answer that exact question directly in your very first sentence.
2. Conversation history is provided ONLY for resolving follow-up references (such as "above", "that", "he", "she", or "this").
3. NEVER reuse, repeat, or treat previous assistant answers as factual evidence.
4. For broad questions (e.g. "How can product teams improve retention?"):
   - Synthesize insights across ALL relevant retrieved transcript sources while keeping each expert's ideas clearly separated.
   - Strictly attribute each claim ONLY to the specific expert who stated it in their retrieved transcript (e.g., "Sarah Tavel emphasizes...", "Patrick Campbell recommends...", "Dan Hockenmaier notes...").
   - NEVER combine one expert's idea with another expert's name (e.g., do NOT attribute early user experience to Patrick Campbell if it comes from Sarah Tavel).
   - Do NOT combine two experts' distinct ideas into a single sentence under one expert's attribution.
5. If the retrieved evidence is insufficient to answer the question, return ONLY the exact fallback response:
   "I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."

FORMATTING & GROUNDING:
- Keep answers concise, practical, complete, and grounded (3–5 complete sentences or 3–5 bullet points).
- NEVER stop mid-sentence. Finish every sentence completely with proper punctuation.
- Prioritize fewer complete sentences over a longer incomplete answer.
- Do not repeat the question or include meta-commentary.
- Every substantive claim must remain strictly supported by the retrieved transcript evidence."""

PURE_GREETINGS = {
    "hi", "hii", "hiii",
    "hello",
    "hey", "heyy",
    "howdy",
    "good morning", "good afternoon", "good evening"
}
GREETING_RESPONSE = "Hi! 👋 I'm Lenny's Growth Assistant. What would you like to learn about growth, product, or the Lenny transcripts?"


def is_pure_greeting(question: str) -> bool:
    if not question:
        return False
    cleaned = question.strip().lower().rstrip("!.?").strip()
    return cleaned in PURE_GREETINGS


CAPABILITY_PHRASES = {
    "what are you capable of",
    "what can you do",
    "what can you help me with",
    "what can you help with",
    "what do you do",
    "how can you help",
    "how can you help me",
    "what features do you have",
    "tell me about yourself",
    "who are you",
    "what is your capability",
    "what are your capabilities",
}

CAPABILITY_RESPONSE = (
    "I'm Lenny's Growth Assistant! Here is what I can help you with:\n\n"
    "• **Grounded Product & Growth Insights**: Ask questions about product management, growth, strategy, and startup advice grounded strictly in Lenny's Podcast transcripts.\n"
    "• **Source Citations**: Every answer includes episode and guest citations so you can trace claims directly to original transcripts.\n"
    "• **Conversational Context**: Follow-up questions are resolved dynamically using multi-turn session history.\n"
    "• **Artifact Generation**: Request structured Markdown guides or self-contained HTML documents and UI components.\n"
    "• **Multi-Provider LLM Engine**: Powered locally by Ollama, with fallback support for cloud providers."
)


def is_capability_question(question: str) -> bool:
    if not question:
        return False
    cleaned = question.strip().lower().rstrip("!.?").strip()
    if cleaned in CAPABILITY_PHRASES:
        return True
    core_triggers = [
        "what are you capable of",
        "what can you do",
        "what can you help me with",
        "what do you do",
        "how can you help",
        "what features do you have",
        "tell me about yourself"
    ]
    return any(trigger in cleaned for trigger in core_triggers)




def analyze_query(question: str) -> dict:
    """
    Extract target expert (if named) and main topic keywords/phrases from the query.
    """
    from database import SessionLocal
    from models import TranscriptChunk

    q_lower = question.lower()

    db = SessionLocal()
    try:
        episodes = db.query(TranscriptChunk.episode).distinct().all()
        known_experts = list(set([e[0] for e in episodes if e[0]]))
    except Exception:
        known_experts = [
            "Patrick Campbell", "Sarah Tavel", "Dan Hockenmaier", "Janna Bastow",
            "Elena Verna", "Uri Levine", "Jeanne Grosser", "Christopher Lochhead",
            "Mayur Kamat", "Jag Duggal", "Annie Duke", "Gina Gotthilf", "Adam Fishman",
            "Ronny Kohavi", "Hila Qu", "Bob Baxley", "Austin Hay", "Brian Chesky",
            "Tomer Cohen", "Annie Pearl", "Jake Knapp", "John Zeratsky", "Varun Mohan",
            "Christian Idiodi", "Shreyas Doshi", "Lenny Rachitsky"
        ]
    finally:
        db.close()

    target_expert = None
    for expert in known_experts:
        parts = expert.split()
        if expert.lower() in q_lower:
            target_expert = expert
            break
        elif len(parts) >= 2 and (parts[0].lower() in q_lower and parts[1].lower() in q_lower):
            target_expert = expert
            break

    stopwords = {
        "what", "is", "are", "was", "were", "does", "do", "did", "say", "says", "said",
        "about", "on", "in", "for", "to", "from", "with", "by", "of", "how", "can",
        "should", "could", "would", "tell", "me", "something", "advice", "perspective",
        "think", "thinks", "product", "teams", "team", "the", "a", "an", "and", "or",
        "lenny", "rachitsky", "transcript", "transcripts", "according"
    }
    if target_expert:
        for p in target_expert.lower().split():
            stopwords.add(p)

    raw_tokens = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", q_lower) if w not in stopwords]

    topic_synonyms = {
        "measuring": ["measure", "measuring", "metrics", "cohort", "cohorts", "active", "core action"],
        "measure": ["measure", "measuring", "metrics", "cohort", "cohorts", "active", "core action"],
        "cancellation": ["cancellation", "cancel", "offboarding", "salvage", "churn"],
        "cancellations": ["cancellation", "cancel", "offboarding", "salvage", "churn"],
        "flows": ["flow", "flows", "funnel", "offboarding"],
        "retention": ["retention", "retain", "retaining", "churn", "cohorts"],
        "design": ["design", "structure"],
        "org": ["org", "organization", "organizational"]
    }

    expanded_tokens = set(raw_tokens)
    for t in raw_tokens:
        if t in topic_synonyms:
            expanded_tokens.update(topic_synonyms[t])

    return {
        "expert": target_expert,
        "topic_tokens": expanded_tokens,
        "raw_query_tokens": raw_tokens,
        "raw_query": question,
    }


def select_evidence(question: str, analysis: dict, limit: int = 3):
    """
    Select focused, high-quality evidence passages matching query topic and expert preference.
    """
    from database import SessionLocal
    from models import TranscriptChunk

    target_expert = analysis["expert"]
    topic_tokens = analysis["topic_tokens"]
    raw_query_tokens = analysis["raw_query_tokens"]

    vector_candidates = search_similar_chunks(question, limit=20)

    selected_chunks = []
    expert_has_substantive_evidence = True

    if target_expert:
        db = SessionLocal()
        try:
            db_expert_chunks = db.query(TranscriptChunk).filter(
                TranscriptChunk.episode.ilike(f"%{target_expert}%")
            ).all()

            scored_expert_chunks = []
            for c in db_expert_chunks:
                c_text = (c.content or "").lower()
                raw_hits = sum(1 for t in raw_query_tokens if t in c_text)
                syn_hits = sum(1 for t in topic_tokens if t in c_text)

                phrase_bonus = 0
                if any(p in c_text for p in ["cancellation flow", "cancellation flows", "offboarding", "salvage"]):
                    phrase_bonus += 10
                if any(p in c_text for p in ["core action", "weekly active", "cohort", "measuring retention"]):
                    phrase_bonus += 10

                score = (raw_hits * 3) + syn_hits + phrase_bonus
                if score > 0:
                    scored_expert_chunks.append((score, raw_hits, c))

            scored_expert_chunks.sort(key=lambda x: x[0], reverse=True)

            if not scored_expert_chunks:
                expert_has_substantive_evidence = False
            else:
                has_dedicated_evidence = False
                for _, raw_hits, c in scored_expert_chunks:
                    c_lower = (c.content or "").lower()
                    if "cancellation" in raw_query_tokens or "flows" in raw_query_tokens:
                        if any(term in c_lower for term in ["cancellation flow", "cancel flow", "offboarding", "salvage"]):
                            has_dedicated_evidence = True
                            break
                    elif "measuring" in raw_query_tokens or "measure" in raw_query_tokens or "cohort" in raw_query_tokens:
                        if any(term in c_lower for term in ["core action", "weekly active", "cohort", "measuring retention"]):
                            has_dedicated_evidence = True
                            break
                    elif "org" in raw_query_tokens or "design" in raw_query_tokens:
                        if "org design" in c_lower or "organizational design" in c_lower:
                            if any(term in c_lower for term in ["structure", "hierarchy", "department", "reporting"]):
                                has_dedicated_evidence = True
                                break
                        has_dedicated_evidence = False
                    else:
                        if raw_hits >= 1 or len(scored_expert_chunks) > 0:
                            has_dedicated_evidence = True
                            break

                if not has_dedicated_evidence:
                    expert_has_substantive_evidence = False
                else:
                    for _, _, c in scored_expert_chunks:
                        if len(selected_chunks) < limit:
                            c_lower = (c.content or "").lower()
                            if any(term in c_lower for term in ["cancellation", "offboarding", "salvage", "core action", "active user", "measuring", "cohort"]):
                                if c not in selected_chunks:
                                    selected_chunks.append(c)

                    if not selected_chunks and scored_expert_chunks:
                        selected_chunks.append(scored_expert_chunks[0][2])
        finally:
            db.close()

    seen_episodes = {getattr(c, "episode", None) for c in selected_chunks if hasattr(c, "episode") and c.episode}
    seen_ids = {getattr(c, "id", None) for c in selected_chunks if hasattr(c, "id")}

    if not target_expert or expert_has_substantive_evidence:
        for cand in vector_candidates:
            cand_id = getattr(cand, "id", None)
            if cand_id and cand_id in seen_ids:
                continue
            ep = getattr(cand, "episode", None) or getattr(cand, "title", None) or "Unknown"
            cand_text = (getattr(cand, "content", "") or "").lower()

            if "retention" in raw_query_tokens or "improve" in raw_query_tokens:
                if not any(term in cand_text for term in ["retention", "retain", "churn", "cohort", "experience", "onboarding"]):
                    continue

            if target_expert:
                if ep == target_expert or len(selected_chunks) < limit:
                    selected_chunks.append(cand)
                    seen_ids.add(cand_id)
            else:
                if ep not in seen_episodes:
                    selected_chunks.append(cand)
                    seen_episodes.add(ep)
                    seen_ids.add(cand_id)
            if len(selected_chunks) >= limit:
                break

    return selected_chunks[:limit], expert_has_substantive_evidence


def build_focused_context(chunks):
    """
    Format evidence passages with explicit boundaries.
    """
    context_parts = []
    for idx, c in enumerate(chunks, start=1):
        guest = getattr(c, "episode", "Unknown Expert")
        title = getattr(c, "title", "Unknown Episode")
        content = (getattr(c, "content", "") or "").strip()[:1000]

        context_parts.append(
            f"SOURCE {idx}\nExpert: {guest}\nEpisode: {title}\nContent:\n{content}"
        )
    return "\n\n".join(context_parts)


build_context = build_focused_context



FALLBACK_MSG = "I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently."


def clean_answer_text(text: str) -> str:
    """
    Strip any appended fallback sentence or disclaimer from the generated answer,
    and ensure the response does not end with an incomplete fragment mid-sentence.
    """
    if not text:
        return text

    disclaimer_patterns = [
        r"\n*\s*(Note:?\s*)?I don't have enough evidence in the retrieved Lenny transcripts to answer that confidently\.?\s*$",
        r"\n*\s*(Note:?\s*)?The available Lenny transcript sources do not provide enough information\.?\s*$",
        r"\n*\s*(Note:?\s*)?Based on the provided context, I don't have enough evidence\.?\s*$",
    ]

    cleaned = text.strip()
    for pat in disclaimer_patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()

    # If response ends mid-sentence (no valid trailing punctuation), strip incomplete fragment
    valid_endings = (".", "!", "?", ":", '"', "'", ")", "]", "`")
    if cleaned and not cleaned.endswith(valid_endings):
        last_punct = max(
            cleaned.rfind("."),
            cleaned.rfind("!"),
            cleaned.rfind("?"),
            cleaned.rfind(":"),
        )
        if last_punct != -1:
            cleaned = cleaned[: last_punct + 1].strip()

    return cleaned.strip()



def validate_grounding(raw_answer: str, analysis: dict, chunks: list, expert_has_substantive_evidence: bool = True) -> tuple[bool, str, str]:
    """
    Robust, non-brittle grounding validation.
    Returns: (is_valid, cleaned_answer, reason)
    """
    cleaned_main = clean_answer_text(raw_answer)

    if not cleaned_main:
        return False, FALLBACK_MSG, "Empty answer after cleaning"

    target_expert = analysis["expert"]

    if target_expert and not expert_has_substantive_evidence:
        return False, FALLBACK_MSG, "Insufficient substantive evidence for named expert topic"

    if FALLBACK_MSG.lower() in cleaned_main.lower() and len(cleaned_main) <= len(FALLBACK_MSG) + 15:
        return False, FALLBACK_MSG, "Standalone fallback response"

    if target_expert:
        first_name = target_expert.split()[0].lower()
        last_name = target_expert.split()[-1].lower()
        ans_lower = cleaned_main.lower()
        if first_name not in ans_lower and last_name not in ans_lower:
            return False, FALLBACK_MSG, f"Named expert {target_expert} not mentioned in answer"

    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by",
        "about", "this", "that", "from", "be", "been", "being", "have", "has", "had",
        "is", "are", "was", "were", "does", "do", "did", "say", "says", "said", "also",
        "more", "less", "can", "could", "would", "should", "not", "but", "which", "what"
    }

    answer_words = set([w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", cleaned_main) if w.lower() not in stopwords])
    chunk_text = " ".join([(getattr(c, "content", "") or "").lower() for c in chunks])
    chunk_words = set([w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", chunk_text) if w.lower() not in stopwords])

    overlap_words = answer_words & chunk_words

    if len(answer_words) >= 5 and len(overlap_words) == 0:
        return False, FALLBACK_MSG, "No token overlap between answer and evidence"

    return True, cleaned_main, "Passed validation"


def format_sources(results):
    """Extract deduplicated source metadata from search results."""
    sources = []
    seen = set()

    for result in results:
        guest = getattr(result, "episode", "Unknown guest")
        title = getattr(result, "title", "Unknown episode")
        url = getattr(result, "source_url", "")
        chunk_index = getattr(result, "chunk_index", 0)

        key = (guest, title, url, chunk_index)
        if key in seen:
            continue
        seen.add(key)

        sources.append({
            "guest": guest,
            "title": title,
            "url": url,
            "chunk_index": chunk_index,
        })
    return sources


def is_conversational_followup(question: str) -> bool:
    """
    Determine if a question is a conversational follow-up relying on previous context.
    """
    if not question:
        return False

    q_lower = question.lower().strip()
    words = re.findall(r"\b[a-zA-Z]{2,}\b", q_lower)

    # 1. Anaphoric / demonstrative pronouns & explicit reference words
    explicit_ref_words = {
        "above", "earlier", "previous", "that", "this", "it",
        "he", "she", "they", "those", "these"
    }

    if any(w in explicit_ref_words for w in words):
        return True

    # 2. Key follow-up phrases
    followup_phrases = [
        "more simply", "simplify", "elaborate", "tell me more",
        "explain more", "can you explain", "what about"
    ]
    if any(p in q_lower for p in followup_phrases):
        return True

    # 3. Short queries starting with why / how / explain (<= 4 words)
    if len(words) <= 4:
        if words and words[0] in {"why", "how", "explain", "elaborate"}:
            return True

    return False


def contextualize_query(question: str, conversation_history: list[dict] = None) -> str:
    """
    Construct a standalone retrieval query for conversational follow-ups.
    If question is a follow-up and history exists, merge previous topic/expert context.
    Otherwise return question unchanged.
    """
    if not conversation_history:
        return question

    if not is_conversational_followup(question):
        return question

    user_msgs = [
        msg.get("content", "").strip()
        for msg in reversed(conversation_history)
        if msg.get("role") == "user" and msg.get("content", "").strip()
    ]

    if not user_msgs:
        return question

    last_user_msg = user_msgs[0]
    return f"{last_user_msg} {question}"


def generate_chat_response(
    question: str,
    conversation_history: list[dict] = None,
    limit: int = 3,
    provider: str = "ollama",
) -> dict:
    """
    Generate a grounded chat response using focused context RAG and validation.
    """
    if is_pure_greeting(question):
        return {
            "message": GREETING_RESPONSE,
            "sources": [],
            "provider": provider,
        }

    if is_capability_question(question):
        return {
            "message": CAPABILITY_RESPONSE,
            "sources": [],
            "provider": provider,
        }

    t_retrieval_start = time.perf_counter()
    retrieval_query = contextualize_query(question, conversation_history)
    analysis = analyze_query(retrieval_query)
    chunk_limit = 2 if analysis.get("expert") else max(1, limit)
    results, expert_has_substantive = select_evidence(retrieval_query, analysis, limit=chunk_limit)
    sources = format_sources(results)
    t_retrieval_end = time.perf_counter()
    retrieval_duration = t_retrieval_end - t_retrieval_start

    print(f"[STAGE 3] Semantic Retrieval finished in {retrieval_duration:.4f}s (Selected chunks: {len(results)}, Substantive: {expert_has_substantive})")

    # Fast-path for ungrounded named expert topics
    if analysis["expert"] and not expert_has_substantive:
        return {
            "message": FALLBACK_MSG,
            "sources": [],
            "provider": provider,
        }

    if not results:
        return {
            "message": FALLBACK_MSG,
            "sources": [],
            "provider": provider,
        }

    t_prompt_start = time.perf_counter()
    context = build_focused_context(results)

    history_text = ""
    if conversation_history:
        history_parts = []
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "").strip()
            history_parts.append(f"{role}: {content}")
        history_text = "\n".join(history_parts)

    user_prompt_content = f"""RETRIEVED TRANSCRIPT EVIDENCE:
{context}

CONVERSATION HISTORY (FOR REFERENCE RESOLUTION ONLY - DO NOT USE AS EVIDENCE):
{history_text if history_text else "None"}

QUESTION TO ANSWER:
{question}

Instructions:
- Provide a direct answer to "QUESTION TO ANSWER" using the retrieved transcript evidence.
- Keep each expert's points clearly separated.
- Strictly attribute each point ONLY to the expert who stated it in the evidence (e.g., Sarah Tavel for early user experience, Patrick Campbell for cancellation flows, Dan Hockenmaier for growth models/levers).
- Do not mix or swap expert names between different advice points.
- Ensure every sentence is complete and ends with proper punctuation. Never truncate or stop mid-sentence.
- Do not copy or repeat previous assistant responses."""

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt_content,
        },
    ]

    t_prompt_end = time.perf_counter()
    prompt_duration = t_prompt_end - t_prompt_start

    total_prompt_chars = sum(len(m["content"]) for m in messages)
    approx_tokens = total_prompt_chars // 4
    selected_model = os.getenv("CHAT_MODEL", "llama3.2:1b")

    print(f"[STAGE 4] Prompt Construction finished in {prompt_duration:.4f}s")
    print(f"          - Selected Provider: {provider}")
    print(f"          - Selected Model: {selected_model}")
    print(f"          - Number of Retrieved Chunks: {len(results)}")
    print(f"          - Approx Prompt Size: {total_prompt_chars} chars (~{approx_tokens} tokens)")

    try:
        t_gen_start = time.perf_counter()
        print(f"[STAGE 5] Ollama Generation START at {time.strftime('%H:%M:%S')}")
        raw_answer = query_llm(messages, temperature=0.1, provider=provider)
        t_gen_end = time.perf_counter()
        gen_duration = t_gen_end - t_gen_start
        print(f"[STAGE 6] Ollama Generation END at {time.strftime('%H:%M:%S')} (Duration: {gen_duration:.4f}s)")

        valid, final_answer, reason = validate_grounding(raw_answer, analysis, results, expert_has_substantive)
        print(f"[GROUNDING VALIDATION] Valid: {valid} ({reason})")

        return {
            "message": final_answer,
            "sources": sources if valid else [],
            "provider": provider,
        }
    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {exc}") from exc


def diversify_sources(results, max_per_episode=1, limit=5):
    """Select diverse transcript sources while limiting repeated episodes."""
    selected = []
    episode_counts = {}

    for result in results:
        episode = getattr(result, "episode", None) or getattr(result, "title", None) or "Unknown"

        if episode_counts.get(episode, 0) >= max_per_episode:
            continue

        selected.append(result)
        episode_counts[episode] = episode_counts.get(episode, 0) + 1

        if len(selected) >= limit:
            break

    return selected


def generate_artifact(
    prompt: str,
    format: str = "markdown",
    conversation_history: list[dict] = None,
    limit: int = 5,
    provider: str = "ollama",
) -> dict:
    """
    Generate a grounded Markdown or standalone HTML artifact using transcript RAG.
    """
    raw_results = search_similar_chunks(
        query=prompt,
        limit=15,
    )

    results = diversify_sources(raw_results, max_per_episode=1, limit=limit)

    context = build_context(results) if results else "No direct transcript matches found."

    history_text = ""
    if conversation_history:
        history_parts = []
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "").strip()
            history_parts.append(f"{role}: {content}")
        history_text = "\n".join(history_parts)

    if format == "html":
        format_instructions = """Generate a standalone, complete HTML document starting with <!DOCTYPE html> and containing <html><head> and <body>.
Include clean inline CSS in a <style> block for elegant styling (modern fonts, responsive container, clean typography, dark theme background #0f172a, card containers, clear headings).
Do NOT include JavaScript (<script> tags).
The HTML document must be complete, beautifully formatted, and self-contained.
Do NOT wrap the document in code fences (do NOT use ``` or ```html)."""
    else:
        format_instructions = """Generate a clean, structured Markdown document.
Start with a single level-1 heading (# Title).
Use standard Markdown syntax for headings (# Title, ## Section, ### Subsection). Do NOT escape hash symbols (never output \\## or \\#).
Use bullet points, numbered lists, and bold text where appropriate.
Do NOT wrap the document in Markdown code fences (do NOT enclose in ```markdown or ```).
Ensure the content is well-organized and immediately usable."""

    user_prompt_content = f"""Previous conversation:
{history_text if history_text else "None"}

Retrieved transcript context:
{context}

Artifact Request:
{prompt}

Format Requirement:
{format_instructions}

Ground all expert claims strictly in the retrieved context. Never invent stats or opinions.
"""

    try:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\n\nYou are an expert document and artifact generator.",
            },
            {
                "role": "user",
                "content": user_prompt_content,
            },
        ]
        content = query_llm(messages, temperature=0.2, provider=provider)

        # Clean outer backtick code fences if present
        content = re.sub(r"^```(?:html|markdown)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content).strip()

        # Unescape escaped markdown headings if format is markdown
        if format == "markdown":
            content = re.sub(r"^\\+(#+\s+)", r"\1", content, flags=re.MULTILINE)
            content = re.sub(r"\\(#+)", r"\1", content)

        # Extract title from content or generate fallback title
        title = "Generated Artifact"
        if format == "markdown":
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = prompt[:40].title() + ("..." if len(prompt) > 40 else "")
        elif format == "html":
            title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title_match_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.IGNORECASE | re.DOTALL)
                if title_match_h1:
                    clean_h1 = re.sub(r"<[^>]+>", "", title_match_h1.group(1)).strip()
                    if clean_h1:
                        title = clean_h1
                else:
                    title = prompt[:40].title() + ("..." if len(prompt) > 40 else "")

        return {
            "title": title,
            "content": content,
            "format": format,
        }
    except Exception as exc:
        raise RuntimeError(f"Ollama artifact generation failed: {exc}") from exc


def generate_answer(question: str, conversation_history=None):
    """Backwards-compatible wrapper."""
    res = generate_chat_response(
        question=question,
        conversation_history=conversation_history,
        limit=5,
    )
    return {
        "answer": res["message"],
        "sources": res["sources"],
    }

