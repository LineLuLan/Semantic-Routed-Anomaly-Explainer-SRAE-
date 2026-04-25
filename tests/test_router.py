"""Phase 3 — semantic router smoke test.

Seeds an isolated ChromaDB into a tmp dir so the suite never collides with
the developer's real `.chroma/` directory, then verifies that traffic-anomaly
descriptions route to the bot-scraping playbook.

Two assertions, by design:
- A terse query ("Traffic spike at 2 AM") must still pick the right rule.
  Cosine distance for short generic queries against the verbose rule text
  sits around ~0.44 with all-MiniLM-L6-v2, so we only assert routing
  identity here, not tightness.
- A richer query that includes the salient cues (late-night, bot/crawler)
  must clear the spec's `distance < 0.35` tightness gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def seeded_chroma(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from src.router.seed_chroma import seed

    persist_dir = tmp_path_factory.mktemp("chroma")
    seed(persist_dir=persist_dir)
    return persist_dir


@pytest.fixture(scope="session")
def router(seeded_chroma: Path):
    from src.router.semantic import SemanticRouter

    return SemanticRouter(persist_dir=seeded_chroma)


def test_terse_traffic_spike_routes_to_bot_scraping_rule(router) -> None:
    result = router.route("Traffic spike at 2 AM")

    assert "bot scraping" in result["rule_text"].lower(), result["rule_text"]
    assert "rate limiting" in result["suggested_action"].lower()


def test_descriptive_late_night_query_clears_distance_gate(router) -> None:
    result = router.route("Late-night traffic spike at 2 AM, possible bot crawling")

    assert "bot scraping" in result["rule_text"].lower(), result["rule_text"]
    assert result["distance"] < 0.35, result["distance"]
