from pathlib import Path
import re

import yaml

from database import SessionLocal
from models import TranscriptChunk


# Location of the Lenny transcript repository
TRANSCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "lennys-podcast-transcripts"
    / "episodes"
)


def parse_transcript_file(file_path: Path):
    """
    Read one Lenny transcript markdown file and extract:
    - episode metadata
    - transcript text
    """

    text = file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    # Split YAML front matter from transcript
    parts = text.split("---", 2)

    if len(parts) < 3:
        print(f"Skipping invalid file: {file_path}")
        return None

    front_matter = parts[1]
    transcript_body = parts[2]

    # Parse YAML metadata
    metadata = yaml.safe_load(front_matter) or {}

    # Extract transcript section
    transcript_match = re.search(
        r"## Transcript\s*(.*)",
        transcript_body,
        re.DOTALL,
    )

    if not transcript_match:
        print(f"No transcript found: {file_path}")
        return None

    transcript = transcript_match.group(1).strip()

    return {
        "episode": metadata.get("guest"),
        "title": metadata.get("title"),
        "source_url": metadata.get("youtube_url"),
        "content": transcript,
    }


def load_transcripts():
    """
    Load all transcript files into PostgreSQL.
    """

    if not TRANSCRIPTS_DIR.exists():
        raise FileNotFoundError(
            f"Transcript directory not found: {TRANSCRIPTS_DIR}"
        )

    db = SessionLocal()

    try:
        files = list(TRANSCRIPTS_DIR.rglob("*.md"))

        print(f"Found {len(files)} transcript files.")

        count = 0

        for file_path in files:
            data = parse_transcript_file(file_path)

            if not data:
                continue

            # Store the complete transcript for now.
            # Chunking will happen in the next step.
            chunk = TranscriptChunk(
                episode=data["episode"],
                title=data["title"],
                source_url=data["source_url"],
                content=data["content"],
            )

            db.add(chunk)

            count += 1

            if count % 10 == 0:
                db.commit()
                print(f"Loaded {count} transcripts...")

        db.commit()

        print(f"Successfully loaded {count} transcripts.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    load_transcripts()