from database import SessionLocal
from models import TranscriptChunk


BAD_TERMS = [
    "google pixel",
    "samsung galaxy",
    "product information",
    "extract the product",
    "fitness",
    "manufacturer",
    "<span",
    "<div",
    "ignore previous instructions",
    "ignore all previous",
]


def find_bad_chunks():

    db = SessionLocal()

    try:

        chunks = (
            db.query(TranscriptChunk)
            .all()
        )

        bad_count = 0

        for chunk in chunks:

            content = (
                chunk.content or ""
            ).lower()

            matches = [
                term
                for term in BAD_TERMS
                if term in content
            ]

            if matches:

                bad_count += 1

                print("\n" + "=" * 80)

                print(
                    f"ID: {chunk.id}"
                )

                print(
                    f"Guest: {chunk.episode}"
                )

                print(
                    f"Title: {chunk.title}"
                )

                print(
                    f"Chunk: {chunk.chunk_index}"
                )

                print(
                    f"Matched: {matches}"
                )

                print("\nCONTENT:\n")

                print(
                    chunk.content[:2000]
                )

        print("\n" + "=" * 80)

        print(
            f"BAD CHUNKS FOUND: {bad_count}"
        )

    finally:

        db.close()


if __name__ == "__main__":
    find_bad_chunks()