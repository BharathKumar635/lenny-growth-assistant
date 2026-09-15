from database import SessionLocal
from models import TranscriptChunk


CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def split_text(text: str):
    """
    Split text into overlapping chunks based on words.
    """

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE

        chunk = " ".join(words[start:end])

        chunks.append(chunk)

        # Move forward while keeping overlap
        start = end - CHUNK_OVERLAP

    return chunks


def chunk_transcripts():
    db = SessionLocal()

    try:
        # Get the current full transcripts
        transcripts = db.query(TranscriptChunk).all()

        print(f"Found {len(transcripts)} transcript records.")

        # We don't want to modify the table while iterating.
        original_transcripts = transcripts

        # Remove existing records.
        # We will replace them with chunks.
        db.query(TranscriptChunk).delete()

        chunk_count = 0

        for transcript in original_transcripts:

            chunks = split_text(transcript.content)

            for index, chunk_text in enumerate(chunks):

                chunk = TranscriptChunk(
                    episode=transcript.episode,
                    title=transcript.title,
                    source_url=transcript.source_url,
                    timestamp=None,
                    chunk_index=index,
                    content=chunk_text,
                    embedding=None,
                )

                db.add(chunk)

                chunk_count += 1

        db.commit()

        print(f"Created {chunk_count} transcript chunks.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    chunk_transcripts()