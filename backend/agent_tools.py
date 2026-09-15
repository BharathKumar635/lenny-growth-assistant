from search import search_similar_chunks
from skills.ship30 import generate_ship30_essay


def search_lenny_transcripts(query: str, limit: int = 5):
    results = search_similar_chunks(query=query, limit=limit)

    sources = []

    for result in results:
        sources.append({
            "guest": result.episode,
            "title": result.title,
            "url": result.source_url,
            "chunk_index": result.chunk_index,
            "content": result.content,
        })

    return sources


def create_ship30_essay(topic: str, limit: int = 5):
    sources = search_lenny_transcripts(
        query=topic,
        limit=limit,
    )

    return generate_ship30_essay(
        topic=topic,
        transcript_sources=sources,
    )