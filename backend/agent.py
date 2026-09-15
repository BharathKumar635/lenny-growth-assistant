
import ollama

from agent_tools import search_lenny_transcripts


CHAT_MODEL = "llama3.2:3b"


AGENT_SYSTEM_PROMPT = """
You are Lenny Growth Assistant.

You are an AI assistant that answers questions about:

- Product management
- Product growth
- Startups
- Career decisions
- User research
- Product strategy

You have access to Lenny's Podcast transcript knowledge through a
transcript search tool.

IMPORTANT RULES:

1. Use the Lenny transcript search results as your primary source.
2. Do not invent facts, quotes, guests, or episode information.
3. Answer only what the available evidence supports.
4. Ignore advertisements and sponsor messages.
5. If the knowledge base does not contain enough information, clearly say so.
6. Give practical and concise answers.
7. When sources are available, mention the relevant guest or episode.
"""


def run_agent(
    question: str,
    conversation_history=None,
):
    """
    Run the Lenny Growth Assistant agent.

    The agent currently:
    1. Searches the Lenny knowledge base.
    2. Builds context from the search results.
    3. Uses the local Ollama model to generate the answer.
    """

    # ---------------------------------------------------------
    # 1. Search the knowledge base
    # ---------------------------------------------------------

    sources = search_lenny_transcripts(
        query=question,
        limit=3,
    )

    if not sources:
        return {
            "answer": (
                "I couldn't find enough relevant information "
                "in the Lenny transcript knowledge base."
            ),
            "sources": [],
        }

    # ---------------------------------------------------------
    # 2. Build transcript context
    # ---------------------------------------------------------

    context_parts = []

    for index, source in enumerate(sources, start=1):

        # Keep the local model context manageable.
        content = source["content"][:2500]

        context_parts.append(
            f"""
SOURCE {index}

Guest: {source["guest"]}

Episode: {source["title"]}

URL: {source["url"]}

Transcript:

{content}
"""
        )

    context = "\n".join(context_parts)

    # ---------------------------------------------------------
    # 3. Build conversation history
    # ---------------------------------------------------------

    history_text = ""

    if conversation_history:

        history_parts = []

        for message in conversation_history[-6:]:

            history_parts.append(
                f"{message['role'].upper()}: {message['content']}"
            )

        history_text = "\n".join(history_parts)

    # ---------------------------------------------------------
    # 4. Ask the local LLM
    # ---------------------------------------------------------

    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": AGENT_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Previous conversation:

{history_text}

Lenny transcript context:

{context}

Current question:

{question}

Answer the user's question using the transcript context.

Keep the answer concise and practical.
""",
            },
        ],
        options={
            "temperature": 0.1,
            "num_ctx": 4096,
        },
    )

    # ---------------------------------------------------------
    # 5. Extract answer
    # ---------------------------------------------------------

    answer = response["message"]["content"]

    answer = answer.replace("<|output|>", "").strip()

    # ---------------------------------------------------------
    # 6. Return answer + source metadata
    # ---------------------------------------------------------

    return {
        "answer": answer,
        "sources": [
            {
                "guest": source["guest"],
                "title": source["title"],
                "url": source["url"],
                "chunk_index": source["chunk_index"],
            }
            for source in sources
        ],
    }


if __name__ == "__main__":

    result = run_agent(
        "When should I leave my job?"
    )

    print("\n" + "=" * 80)
    print("AGENT ANSWER")
    print("=" * 80)

    print(result["answer"])

    print("\n" + "=" * 80)
    print("SOURCES")
    print("=" * 80)

    for source in result["sources"]:

        print(f"\nGuest: {source['guest']}")
        print(f"Episode: {source['title']}")
        print(f"URL: {source['url']}")
        print(f"Chunk: {source['chunk_index']}")

