import ollama

from database import SessionLocal
from models import TranscriptChunk


EMBEDDING_MODEL = "nomic-embed-text"


def generate_embedding(text: str):
    """Generate a 768-dimensional embedding using Ollama."""

    response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response["embeddings"][0]


def embed_all_chunks():
    db = SessionLocal()

    try:
        chunks = (
            db.query(TranscriptChunk)
            .filter(TranscriptChunk.embedding.is_(None))
            .all()
        )

        total = len(chunks)

        print(f"Found {total} chunks without embeddings.")

        for index, chunk in enumerate(chunks, start=1):

            chunk.embedding = generate_embedding(chunk.content)

            # Save every 50 chunks
            if index % 50 == 0:
                db.commit()
                print(f"Embedded {index}/{total} chunks...")

        db.commit()

        print(f"Successfully embedded {total} chunks.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    embed_all_chunks()