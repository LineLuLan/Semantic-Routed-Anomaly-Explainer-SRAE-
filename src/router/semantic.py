"""ChromaDB-backed semantic router for business rule lookup.

`SemanticRouter.route(text)` returns the closest matching rule along with
its suggested action and the cosine distance to the query.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.config import settings
from src.router.seed_chroma import COLLECTION_NAME, DEFAULT_PERSIST_DIR


class SemanticRouter:
    def __init__(self, persist_dir: Path | str = DEFAULT_PERSIST_DIR) -> None:
        from sentence_transformers import SentenceTransformer

        self._client = chromadb.PersistentClient(path=str(Path(persist_dir)))
        self._collection = self._client.get_collection(COLLECTION_NAME)
        self._model = SentenceTransformer(settings.embedding_model)

    def route(self, text: str) -> dict[str, Any]:
        query_embedding = self._model.encode(
            [text], normalize_embeddings=True
        ).tolist()
        result = self._collection.query(
            query_embeddings=query_embedding,
            n_results=1,
        )

        rule_text = result["documents"][0][0]
        metadata = result["metadatas"][0][0]
        distance = float(result["distances"][0][0])

        return {
            "rule_text": rule_text,
            "suggested_action": metadata["suggested_action"],
            "distance": distance,
        }
