from database import SessionLocal
from models import TranscriptChunk


BAD_TERMS = [
    "Google Pixel 7",
    "Samsung Galaxy S23",
    "Extract the product information",
    "product information:",
    "<div class='product'>",
    "<span class='price'>",
]


def check_garbage():

    db = SessionLocal()

    try:

        for term in BAD_TERMS:

            print("\n" + "=" * 80)
            print(f"SEARCHING FOR: {term}")
            print("=" * 80)

            results = (
                db.query(TranscriptChunk)
                .filter(
                    TranscriptChunk.content.ilike(
                        f"%{term}%"
                    )
                )
                .limit(10)
                .all()
            )

            print(
                f"Matches found: {len(results)}"
            )

            for chunk in results:

                print("\n---")
                print(f"ID: {chunk.id}")
                print(f"Guest: {chunk.episode}")
                print(f"Title: {chunk.title}")
                print(f"Chunk: {chunk.chunk_index}")
                print(
                    chunk.content[:1000]
                )

    finally:

        db.close()


if __name__ == "__main__":
    check_garbage()