"""Reads gold.member_notes_index from Postgres, chunks + embeds each note with
sentence-transformers/all-MiniLM-L6-v2, and upserts into Qdrant. Every point's payload
carries member_id - the ensemble/qdrant retriever always filters on it (see
retrieval/qdrant/retriever.py), which is the mandatory per-member isolation boundary
described in the README."""

import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text

from .chunking import chunk_text
from .schema import CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION, EMBEDDING_DIM, EMBEDDING_MODEL, QDRANT_URL

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://cmip:cmip123@localhost:5432/cmip")
_POINT_NAMESPACE = uuid.UUID("6f6e6f27-9f2b-4e34-8a55-3ff9f4a2b111")


def _fetch_notes() -> list[dict]:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                select note_id, member_id, note_type, note_date, note_text, cohort_tag,
                       provider_id, provider_name, provider_specialty
                from gold.member_notes_index
                """
            )
        ).mappings().all()
    return [dict(r) for r in rows]


def ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION):
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )


def main() -> None:
    notes = _fetch_notes()
    if not notes:
        print("No rows in gold.member_notes_index - run the dbt Gold layer first.")
        return

    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client)
    model = SentenceTransformer(EMBEDDING_MODEL)

    all_chunks: list[str] = []
    all_payloads: list[dict] = []
    all_ids: list[str] = []

    for note in notes:
        chunks = chunk_text(note["note_text"], CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk in enumerate(chunks):
            point_id = str(uuid.uuid5(_POINT_NAMESPACE, f"{note['note_id']}:{i}"))
            all_ids.append(point_id)
            all_chunks.append(chunk)
            all_payloads.append(
                {
                    "member_id": note["member_id"],
                    "note_id": note["note_id"],
                    "chunk_index": i,
                    "text": chunk,
                    "note_type": note["note_type"],
                    "note_date": str(note["note_date"]),
                    "cohort_tag": note["cohort_tag"],
                    "provider_id": note["provider_id"],
                    "provider_name": note["provider_name"],
                    "provider_specialty": note["provider_specialty"],
                }
            )

    print(f"Embedding {len(all_chunks)} chunks from {len(notes)} notes...")
    vectors = model.encode(all_chunks, batch_size=64, show_progress_bar=True, normalize_embeddings=True)

    points = [
        PointStruct(id=pid, vector=vec.tolist(), payload=payload)
        for pid, vec, payload in zip(all_ids, vectors, all_payloads)
    ]

    batch_size = 256
    for start in range(0, len(points), batch_size):
        client.upsert(collection_name=COLLECTION, points=points[start : start + batch_size])

    print(f"Upserted {len(points)} points into Qdrant collection '{COLLECTION}'")


if __name__ == "__main__":
    main()
