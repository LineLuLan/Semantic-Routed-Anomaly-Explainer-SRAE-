"""Seed the ChromaDB `business_rules` collection.

Idempotent: drops the collection if it exists, recreates it with cosine
distance, then loads the 6 playbooks from `rules.py` encoded with
`sentence-transformers/all-MiniLM-L6-v2` (384-dim, normalized).

Run:
    python -m src.router.seed_chroma
"""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb

from src.config import settings
from src.router.rules import BUSINESS_RULES

LOG = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PERSIST_DIR = PROJECT_ROOT / ".chroma"
COLLECTION_NAME = "business_rules"


def seed(persist_dir: Path | str = DEFAULT_PERSIST_DIR) -> int:
    """Encode rules and write them to a fresh ChromaDB collection."""
    from sentence_transformers import SentenceTransformer

    persist_dir = Path(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_dir))

    # Reset the collection so re-runs produce identical state.
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    model = SentenceTransformer(settings.embedding_model)
    rule_texts = [r[0] for r in BUSINESS_RULES]
    embeddings = model.encode(rule_texts, normalize_embeddings=True).tolist()

    ids = [f"rule-{i}" for i in range(len(BUSINESS_RULES))]
    metadatas = [{"suggested_action": action} for _, action in BUSINESS_RULES]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=rule_texts,
        metadatas=metadatas,
    )

    LOG.info(
        "Seeded %d rules into collection '%s' at %s",
        len(BUSINESS_RULES),
        COLLECTION_NAME,
        persist_dir,
    )
    return len(BUSINESS_RULES)


def main() -> None:
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(message)s"
    )
    seed()


if __name__ == "__main__":
    main()
