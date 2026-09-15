import re
import ollama
from sqlalchemy import select, or_

from database import SessionLocal
from models import TranscriptChunk


EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_LIMIT = 5


def generate_query_embedding(query: str):
    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=query,
    )
    return response["embeddings"][0]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def query_terms(query: str) -> list[str]:
    stop_words = {
        "how", "what", "when", "where", "why",
        "can", "should", "could", "would",
        "do", "does", "did",
        "i", "me", "my", "you", "your",
        "the", "a", "an",
        "is", "are", "was", "were",
        "it", "this", "that",
        "to", "of", "and", "or",
        "for", "in", "on", "with",
        "about", "from", "into", "by",
    }

    return [
        word.lower()
        for word in re.findall(
            r"\b[a-zA-Z]+\b",
            query,
        )
        if word.lower() not in stop_words
        and len(word) >= 3
    ]


def search_similar_chunks(
    query: str,
    limit: int = DEFAULT_LIMIT,
):
    """
    Semantic-first hybrid retrieval.

    Vector similarity is the primary ranking signal.
    Lexical matches provide only small boosts.

    Results are also diversified so one episode does not
    dominate the entire evidence set.
    """

    limit = max(1, min(limit, 10))

    db = SessionLocal()

    try:
        # -----------------------------------------------------
        # 1. Semantic retrieval
        # -----------------------------------------------------

        query_embedding = generate_query_embedding(query)

        distance = TranscriptChunk.embedding.cosine_distance(
            query_embedding
        )

        statement = (
            select(
                TranscriptChunk,
                distance.label("distance"),
            )
            .where(
                TranscriptChunk.embedding.is_not(None)
            )
            .order_by(distance)
            .limit(40)
        )

        vector_rows = db.execute(statement).all()

        if not vector_rows:
            return []

        terms = query_terms(query)

        # -----------------------------------------------------
        # 2. Rank candidates
        # -----------------------------------------------------

        scored = []

        for rank, (chunk, vector_distance) in enumerate(
            vector_rows,
            start=1,
        ):
            title = normalize(chunk.title)
            content = normalize(chunk.content)

            similarity = max(
                0.0,
                1.0 - float(vector_distance),
            )

            score = similarity

            # Phrase-level relevance.
            for i in range(len(terms) - 1):
                phrase = (
                    f"{terms[i]} {terms[i + 1]}"
                )

                if phrase in title:
                    score += 0.08

                elif phrase in content:
                    score += 0.025

            # Small title boost.
            for term in terms:
                if term in title:
                    score += 0.012

            # Small semantic-rank boost.
            score += 0.01 / rank

            scored.append(
                (
                    score,
                    chunk,
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # -----------------------------------------------------
        # 3. Diversify episodes
        # -----------------------------------------------------

        selected = []
        episode_counts = {}

        MAX_PER_EPISODE = 2

        for score, chunk in scored:
            episode_key = (
                chunk.episode
                or chunk.title
                or str(chunk.id)
            )

            current_count = episode_counts.get(
                episode_key,
                0,
            )

            if current_count >= MAX_PER_EPISODE:
                continue

            selected.append(chunk)

            episode_counts[episode_key] = (
                current_count + 1
            )

            if len(selected) >= limit:
                break

        # Fill remaining slots if necessary.
        if len(selected) < limit:
            selected_ids = {
                chunk.id
                for chunk in selected
            }

            for score, chunk in scored:
                if chunk.id in selected_ids:
                    continue

                selected.append(chunk)
                selected_ids.add(chunk.id)

                if len(selected) >= limit:
                    break

        return selected

    finally:
        db.close()


if __name__ == "__main__":
    query = input("Query: ").strip()

    results = search_similar_chunks(
        query=query,
        limit=5,
    )

    print(f"\nFound {len(results)} results.\n")

    for index, chunk in enumerate(
        results,
        start=1,
    ):
        print("=" * 80)
        print(f"RESULT {index}")
        print(f"Guest: {chunk.episode}")
        print(f"Title: {chunk.title}")
        print(f"Chunk: {chunk.chunk_index}")
        print(f"URL: {chunk.source_url}")
        print("-" * 80)
        print(chunk.content[:1200])
        print()