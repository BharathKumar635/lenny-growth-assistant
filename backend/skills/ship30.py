import os
import re
import ollama


CHAT_MODEL = os.getenv("SHIP30_MODEL", "llama3.2:3b")

MIN_WORDS = 1000
TARGET_WORDS = 1250
MAX_WORDS = 1400


# ---------------------------------------------------------
# Basic text cleaning & word count
# ---------------------------------------------------------

def clean_text(text: str) -> str:
    """Clean generated text."""
    if not text:
        return ""

    text = text.strip()
    text = re.sub(
        r"^```(?:markdown|md|text)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*```$",
        "",
        text,
    )
    return text.strip()


def count_words(text: str) -> int:
    """Count words."""
    return len(
        re.findall(
            r"\b[\w'-]+\b",
            text,
        )
    )


# ---------------------------------------------------------
# Transcript safety
# ---------------------------------------------------------

SUSPICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all previous instructions",
    r"ignore the system prompt",
    r"system message",
    r"developer message",
    r"you are now",
    r"act as",
    r"follow these instructions",
    r"new instructions",
    r"assistant:",
    r"system:",
    r"user:",
    r"<script",
    r"</script>",
    r"<html",
    r"<div",
    r"<span",
    r"extract the product",
    r"product information:",
]


def contains_suspicious_content(text: str) -> bool:
    """Detect obvious prompt injection or corrupted content."""
    lowered = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            return True
    return False


def sanitize_transcript(text: str) -> str:
    """Remove obvious injected/corrupted content from transcript chunks."""
    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    lines = text.splitlines()
    safe_lines = []
    for line in lines:
        if contains_suspicious_content(line):
            continue
        safe_lines.append(line)

    text = "\n".join(safe_lines)
    text = re.sub(
        r"\s+",
        " ",
        text,
    )
    return text.strip()


# ---------------------------------------------------------
# Evidence construction
# ---------------------------------------------------------

def build_evidence(transcript_sources: list[dict]) -> str:
    """Build safe, compact evidence string for transcript sources."""
    evidence_parts = []

    for index, source in enumerate(
        transcript_sources,
        start=1,
    ):
        raw_content = source.get("content", "")
        if contains_suspicious_content(raw_content):
            continue

        content = sanitize_transcript(raw_content)
        if not content:
            continue

        content = content[:1400]
        guest = source.get("guest") or "Unknown guest"
        title = source.get("title") or "Unknown episode"
        url = source.get("url") or source.get("source_url") or ""
        chunk_index = source.get("chunk_index", "")

        evidence_parts.append(
            f"""
SOURCE {index}
Guest: {guest}
Episode: {title}
URL: {url}
Chunk: {chunk_index}

Transcript evidence:
{content}
"""
        )

    return "\n".join(evidence_parts)


def build_sources_section(sources: list[dict]) -> str:
    """Build source attribution deterministically in Python."""
    lines = ["## Sources", ""]
    seen = set()

    for source in sources:
        guest = source.get("guest") or "Unknown guest"
        title = source.get("title") or "Unknown episode"
        url = source.get("url") or source.get("source_url") or ""

        key = (guest, title, url)
        if key in seen:
            continue
        seen.add(key)

        if url:
            lines.append(f"- **{guest}** — {title} — {url}")
        else:
            lines.append(f"- **{guest}** — {title}")

    return "\n".join(lines)


# ---------------------------------------------------------
# Single-Call System & User Prompts
# ---------------------------------------------------------

SINGLE_CALL_SYSTEM_PROMPT = """
You are a senior product strategy editor and Ship 30 for 30 writing specialist.

Your task is to write a comprehensive, highly practical, grounded 1,200 to 1,350 word product strategy article based strictly on the retrieved transcript evidence provided.

CRITICAL LENGTH RULE:
The output MUST be a long, detailed article of 1,200 to 1,350 words (hard maximum 1,400 words).
Do NOT summarize or write brief bullet points. Write 3 to 4 long, detailed paragraphs for EVERY section below.

CRITICAL EXPERT MAPPING & ATTRIBUTION RULES:
1. Patrick Campbell = Tactical retention, payment failures, cancellation flows, offboarding, term optimization, 25-40% of churn.
2. Dan Hockenmaier = Early customer experience, first week or first month experience, core product levers.
3. Sarah Tavel = Retention measurement, weekly cohorts, active users, core action completion.
4. Janna Bastow = Discovery, asking customer questions, psychological safety, retrospectives (use ONLY as supporting evidence for discovery in the framework; do NOT make her a primary insight header).

STRICT ATTRIBUTION & GROUNDING RULES:
- Never attribute Patrick's ideas to Sarah, Janna, or Dan.
- Never attribute Dan's early-experience ideas to Sarah or Janna.
- Never attribute Sarah's cohort/core-action ideas to Janna.
- Every claim MUST be supported directly by the supplied transcript evidence.
- DO NOT use generic filler like "Research has shown", "Studies prove", "Customers are more likely to", or "This will significantly increase retention". Use precise expert framing like "Patrick Campbell argues...", "Dan Hockenmaier describes...", or "Sarah Tavel recommends...".
- Do NOT invent statistics, studies, quotes, or ungrounded facts.
- Preserve the exact level of certainty used by the experts.

REQUIRED ARTICLE STRUCTURE (Write multiple long, detailed paragraphs for each section to reach ~1,250 words total):

# [Strong, Catchy Headline]

## Hook
[Write 3 long paragraphs (approx 200 words) introducing the hard problem of retention, setting up why product teams fail at retention, and introducing the core insights grounded in expert evidence.]

## Why Retention Is Hard
[Write 3 long paragraphs (approx 200 words) providing a deep analysis of why retention is the hardest growth metric to move and the structural challenges product teams face.]

## 1. Fix Avoidable Churn Before Building More Features
[Write 4 long paragraphs (approx 270 words) based strictly on Patrick Campbell's evidence. Deeply analyze tactical retention, payment failures, cancellation flows, offboarding, and term optimization. Explain why 25-40% of churn is tactical and avoidable.]

## 2. Win the Early Customer Experience
[Write 4 long paragraphs (approx 270 words) based strictly on Dan Hockenmaier's evidence. Deeply analyze customer experience during the first week and first month. Explain how core product levers shape long-term user retention.]

## 3. Measure Retention Through Cohorts and Core Actions
[Write 4 long paragraphs (approx 270 words) based strictly on Sarah Tavel's evidence. Deeply analyze how to measure retention by tracking weekly cohorts, core action completion, and activity levels within cohorts.]

## A Practical Retention Framework
[Write 3 long paragraphs (approx 220 words) providing a step-by-step framework synthesizing Patrick Campbell's tactical retention, Dan Hockenmaier's early experience levers, Sarah Tavel's cohort tracking, and Janna Bastow's customer discovery and retrospectives.]

## What to Do Next
[Write 2 long paragraphs (approx 160 words) concluding with practical takeaways product teams can execute starting this week.]
"""


def ask_llm_single_call(
    topic: str,
    evidence: str,
) -> str:
    """Call the local Ollama model once to generate the full article."""
    user_prompt = f"""Article Topic:
{topic}

Retrieved Transcript Evidence:
{evidence}

Write the complete 1,200 to 1,350 word article following the exact required structure and strict expert attribution rules above.
Write 3 to 4 detailed, long paragraphs for EVERY section so the total length reaches 1,200-1,350 words.
"""

    model_name = os.getenv("SHIP30_MODEL", "llama3.2:3b")

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": SINGLE_CALL_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        options={
            "temperature": 0.3,
            "num_ctx": 4096,
            "num_predict": 2500,
        },
    )

    return clean_text(response["message"]["content"])


# ---------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------

def generate_ship30_essay(
    topic: str,
    transcript_sources,
):
    """
    Fast, reliable single-call Ship30 generation pipeline.
    Uses ONE LLM generation call for the entire article.
    """

    if not transcript_sources:
        return {
            "essay": "I couldn't find enough relevant information in the Lenny transcript knowledge base.",
            "word_count": 0,
            "valid_length": False,
            "attempts": 0,
            "sources": [],
        }

    evidence = build_evidence(transcript_sources)

    if not evidence:
        return {
            "essay": "The retrieved transcript evidence could not be safely used to generate an answer.",
            "word_count": 0,
            "valid_length": False,
            "attempts": 0,
            "sources": [],
        }

    print("Generating complete article in a single LLM call...", flush=True)

    raw_article = ask_llm_single_call(
        topic=topic,
        evidence=evidence,
    )

    # Remove any accidental Sources section generated by LLM
    cleaned_article = re.split(
        r"\n#+\s*Sources\b",
        raw_article,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()

    # Post-process to remove generic filler phrases if any leaked through
    cleaned_article = re.sub(
        r"\b(research has shown|studies prove|studies show|it has been proven)\b",
        "transcript evidence indicates",
        cleaned_article,
        flags=re.IGNORECASE,
    )

    # Append deterministic Sources section
    final_article = cleaned_article + "\n\n" + build_sources_section(transcript_sources)

    word_count = count_words(final_article)

    # Bad output check
    bad_output = any(
        re.search(pattern, final_article.lower())
        for pattern in [
            r"<div",
            r"<span",
            r"<html",
            r"<script",
            r"google pixel",
            r"samsung galaxy",
            r"extract the product",
            r"product information:",
        ]
    )

    valid_length = MIN_WORDS <= word_count <= MAX_WORDS and not bad_output

    return {
        "essay": final_article,
        "word_count": word_count,
        "valid_length": valid_length,
        "attempts": 1,
        "sources": transcript_sources,
        "outline": "Generated via Single-Call Pipeline",
    }


def generate_ship30(
    topic: str,
    transcript_sources,
):
    """Backwards-compatible wrapper."""
    return generate_ship30_essay(
        topic=topic,
        transcript_sources=transcript_sources,
    )
