"""LLM-based anomaly explainer (Phase 4).

Takes one anomaly dict (from `AnomalyDetector.detect()`) plus the matched
rule dict (from `SemanticRouter.route()`) and produces a short English
report fit for an on-call channel.

Two modes:

* `mock=True` — deterministic template, no network. Used by unit tests and
  by callers that want a predictable string for development without a
  Groq key.
* `mock=False` — real Groq Chat Completions call using `settings.groq_model`.

v0.2 additions
--------------
- Handles the null-rule case (router returned no match above the
  confidence threshold) with a "manual triage required" template /
  prompt instead of pretending a wrong rule is the cause.
- `explain_many` runs Groq calls concurrently in a thread-pool. With
  `limit=10` against `llama-3.1-8b-instant` this drops the user-visible
  /analyze latency from ~5 s sequential to ~1 s.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

from src.config import settings


SYSTEM_PROMPT = (
    "You are an on-call SRE assistant. Given a numerical anomaly and the "
    "matched playbook rule, write ONE concise English paragraph (3-5 sentences) "
    "for an on-call channel. State what happened, when, the metric and value, "
    "the likely cause from the rule, and the suggested next action. "
    "Be factual, no marketing tone, no bullet points."
)

SYSTEM_PROMPT_NO_MATCH = (
    "You are an on-call SRE assistant. The anomaly detector flagged a value "
    "but the playbook router could not find a confident match. Write ONE "
    "concise English paragraph (3-5 sentences) describing the anomaly and "
    "explicitly recommending manual triage — there is no canned remediation. "
    "Be factual, no marketing tone, no bullet points."
)

# Cap on concurrent Groq requests. Groq's free tier is generous but not
# infinite; 8 keeps us well under per-minute caps for limit=10.
_MAX_CONCURRENCY = 8


def _has_rule(rule: dict[str, Any]) -> bool:
    return bool(rule.get("rule_text")) and bool(rule.get("suggested_action"))


def _format_user_prompt(anomaly: dict[str, Any], rule: dict[str, Any]) -> str:
    if _has_rule(rule):
        return (
            "Anomaly:\n"
            f"- timestamp: {anomaly.get('timestamp')}\n"
            f"- metric: {anomaly.get('metric')}\n"
            f"- value: {anomaly.get('value')}\n"
            f"- status: {anomaly.get('status')}\n"
            "\n"
            "Matched rule:\n"
            f"- rule_text: {rule.get('rule_text')}\n"
            f"- suggested_action: {rule.get('suggested_action')}\n"
        )
    return (
        "Anomaly (no matching playbook above the confidence threshold):\n"
        f"- timestamp: {anomaly.get('timestamp')}\n"
        f"- metric: {anomaly.get('metric')}\n"
        f"- value: {anomaly.get('value')}\n"
        f"- status: {anomaly.get('status')}\n"
        f"- best cosine distance: {rule.get('distance')}\n"
    )


def _mock_report(anomaly: dict[str, Any], rule: dict[str, Any]) -> str:
    if _has_rule(rule):
        return (
            f"[MOCK] Anomaly detected on metric '{anomaly.get('metric')}' at "
            f"{anomaly.get('timestamp')} with value {anomaly.get('value')} "
            f"(status={anomaly.get('status')}). "
            f"Matched playbook: {rule.get('rule_text')} "
            f"Suggested action: {rule.get('suggested_action')}."
        )
    return (
        f"[MOCK] Anomaly detected on metric '{anomaly.get('metric')}' at "
        f"{anomaly.get('timestamp')} with value {anomaly.get('value')} "
        f"(status={anomaly.get('status')}). No playbook match above the "
        f"confidence threshold (best distance "
        f"{rule.get('distance')}). Manual triage required."
    )


class Explainer:
    """Wraps Groq chat completions for anomaly explanation."""

    def __init__(self, mock: bool = False) -> None:
        self.mock = mock
        self._client = None
        if not mock:
            if not settings.has_groq_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Either populate .env or "
                    "instantiate Explainer(mock=True) for offline use."
                )
            from groq import Groq

            self._client = Groq(api_key=settings.groq_api_key)

    def explain(self, anomaly: dict[str, Any], rule: dict[str, Any]) -> str:
        if self.mock:
            return _mock_report(anomaly, rule)

        assert self._client is not None
        system_prompt = SYSTEM_PROMPT if _has_rule(rule) else SYSTEM_PROMPT_NO_MATCH
        completion = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _format_user_prompt(anomaly, rule)},
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content.strip()

    def explain_many(
        self, items: Iterable[tuple[dict[str, Any], dict[str, Any]]]
    ) -> list[str]:
        """Explain a batch of (anomaly, rule) pairs.

        Mock mode maps in-process. Live mode parallelizes Groq calls so
        /analyze with limit=10 isn't sequential. Order is preserved.
        """
        item_list = list(items)
        if not item_list:
            return []
        if self.mock:
            return [_mock_report(a, r) for a, r in item_list]

        max_workers = min(_MAX_CONCURRENCY, len(item_list))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(lambda ar: self.explain(*ar), item_list))
