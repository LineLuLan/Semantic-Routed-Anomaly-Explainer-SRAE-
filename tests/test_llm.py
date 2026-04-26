"""Tests for the Phase 4 LLM Explainer.

Mock-mode tests run offline. The integration test that hits Groq is
guarded by `skipif` on `settings.has_groq_key` so the suite stays green
without a key (and works as a smoke test when one is configured).

Note on the marker: PLAN.md mentions a `@pytest.mark.requires_groq`
marker, but `pytest.ini` enforces `--strict-markers` and Phase 4's edit
scope excludes `pytest.ini` and `conftest.py`. `pytest.mark.skipif` gives
the same skip-without-key behaviour without registering a new marker.
"""

from __future__ import annotations

import pytest

from src.config import settings
from src.llm import Explainer
from src.llm.explainer import SYSTEM_PROMPT, _format_user_prompt


ANOMALY = {
    "timestamp": "2026-04-25T01:00:00",
    "metric": "traffic",
    "value": 5000.0,
    "status": "anomaly",
}

RULE = {
    "rule_text": "High late-night traffic indicates bot scraping.",
    "suggested_action": "Check firewall logs.",
    "distance": 0.12,
}


def test_mock_explain_returns_string() -> None:
    explainer = Explainer(mock=True)
    report = explainer.explain(ANOMALY, RULE)

    assert isinstance(report, str)
    assert report  # non-empty


def test_mock_explain_is_deterministic() -> None:
    explainer = Explainer(mock=True)
    a = explainer.explain(ANOMALY, RULE)
    b = explainer.explain(ANOMALY, RULE)

    assert a == b


def test_mock_explain_includes_anomaly_and_rule_fields() -> None:
    explainer = Explainer(mock=True)
    report = explainer.explain(ANOMALY, RULE)

    assert ANOMALY["metric"] in report
    assert str(ANOMALY["value"]) in report
    assert ANOMALY["timestamp"] in report
    assert RULE["rule_text"] in report
    assert RULE["suggested_action"] in report


def test_mock_does_not_require_groq_key() -> None:
    # Should construct successfully even with an empty/placeholder key.
    explainer = Explainer(mock=True)
    assert explainer.mock is True
    assert explainer._client is None


def test_mock_explain_handles_null_rule() -> None:
    """When the router returns no match the mock report must still be
    informative and explicitly call out manual triage."""
    explainer = Explainer(mock=True)
    null_rule = {
        "rule_text": None,
        "suggested_action": None,
        "distance": 0.78,
        "confidence": "low",
    }
    report = explainer.explain(ANOMALY, null_rule)

    assert "manual triage" in report.lower()
    assert "0.78" in report or "0.7" in report


def test_explain_many_mock_preserves_order() -> None:
    explainer = Explainer(mock=True)
    null_rule = {"rule_text": None, "suggested_action": None, "distance": 0.9, "confidence": "low"}
    pairs = [
        (ANOMALY, RULE),
        (ANOMALY, null_rule),
        (ANOMALY, RULE),
    ]
    out = explainer.explain_many(pairs)
    assert len(out) == 3
    assert "manual triage" in out[1].lower()
    assert "manual triage" not in out[0].lower()


def test_real_mode_without_key_raises() -> None:
    if settings.has_groq_key:
        pytest.skip("GROQ_API_KEY is configured; cannot test the missing-key branch.")

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        Explainer(mock=False)


def test_format_user_prompt_contains_all_fields() -> None:
    prompt = _format_user_prompt(ANOMALY, RULE)

    for value in (
        ANOMALY["timestamp"],
        ANOMALY["metric"],
        str(ANOMALY["value"]),
        ANOMALY["status"],
        RULE["rule_text"],
        RULE["suggested_action"],
    ):
        assert value in prompt


def test_system_prompt_is_nonempty_string() -> None:
    assert isinstance(SYSTEM_PROMPT, str)
    assert SYSTEM_PROMPT.strip()


@pytest.mark.skipif(
    not settings.has_groq_key,
    reason="GROQ_API_KEY not set; skipping live Groq integration test.",
)
def test_live_groq_explain_returns_text() -> None:
    """Integration smoke test — only runs when a real key is configured."""
    explainer = Explainer(mock=False)
    report = explainer.explain(ANOMALY, RULE)

    assert isinstance(report, str)
    assert len(report) > 20
