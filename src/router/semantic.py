"""ChromaDB-backed semantic router for business rule lookup.

`SemanticRouter.route(text)` returns the closest matching rule along with
its suggested action and the cosine distance to the query.

v0.2 additions
--------------
- Threshold-based null routing: if the best cosine distance exceeds
  `min_distance` the router returns a null match instead of forcing a
  poor rule onto the anomaly. The Explainer falls back to a "manual
  triage" template in this case.
- Confidence band ("high" / "med" / "low") derived from distance, surfaced
  to the API + UI so reviewers can see at a glance how trustworthy the
  match is.
- Batched query path `route_many(texts)` — one SentenceTransformer encode
  + one Chroma query for the whole batch. Cuts /analyze latency for
  limit=10 from ~10 sequential round-trips down to 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import chromadb

from src.config import settings
from src.router.seed_chroma import COLLECTION_NAME, DEFAULT_PERSIST_DIR

# Default cutoff for "this match is good enough to act on". Cosine distance
# on all-MiniLM-L6-v2 across our 6 rules empirically clusters under 0.45 for
# clear matches; above that the rule text is essentially noise.
DEFAULT_MIN_DISTANCE = 0.45

# Bucketing thresholds for the confidence band shown in the UI.
_HIGH_CUTOFF = 0.30
_MED_CUTOFF = 0.45


def confidence_band(distance: float) -> str:
    """Map cosine distance into a coarse confidence label."""
    if distance < _HIGH_CUTOFF:
        return "high"
    if distance < _MED_CUTOFF:
        return "med"
    return "low"


class SemanticRouter:
    def __init__(
        self,
        persist_dir: Path | str = DEFAULT_PERSIST_DIR,
        min_distance: float = DEFAULT_MIN_DISTANCE,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self._client = chromadb.PersistentClient(path=str(Path(persist_dir)))
        self._collection = self._client.get_collection(COLLECTION_NAME)
        self._model = SentenceTransformer(settings.embedding_model)
        self.min_distance = min_distance

    def _build_result(
        self, rule_text: str, suggested_action: str, distance: float
    ) -> dict[str, Any]:
        confidence = confidence_band(distance)
        if distance > self.min_distance:
            # Honest "no match" — better than a confident wrong playbook.
            return {
                "rule_text": None,
                "suggested_action": None,
                "distance": distance,
                "confidence": confidence,
            }
        return {
            "rule_text": rule_text,
            "suggested_action": suggested_action,
            "distance": distance,
            "confidence": confidence,
        }

    def route(self, text: str) -> dict[str, Any]:
        return self.route_many([text])[0]

    def route_many(self, texts: Iterable[str]) -> list[dict[str, Any]]:
        """Route a batch of queries with a single encode + Chroma round-trip."""
        text_list = list(texts)
        if not text_list:
            return []

        query_embeddings = self._model.encode(
            text_list, normalize_embeddings=True
        ).tolist()
        result = self._collection.query(
            query_embeddings=query_embeddings,
            n_results=1,
        )

        results: list[dict[str, Any]] = []
        for i in range(len(text_list)):
            rule_text = result["documents"][i][0]
            metadata = result["metadatas"][i][0]
            distance = float(result["distances"][i][0])
            results.append(
                self._build_result(rule_text, metadata["suggested_action"], distance)
            )
        return results
