"""LLM-based anomaly explainer (Phase 4).

Takes one anomaly dict (from `AnomalyDetector.detect()`) plus the matched
rule dict (from `SemanticRouter.route()`) and produces a short English
report fit for an on-call channel.

Two modes:

* `mock=True` — deterministic template, no network. Used by unit tests and
  by callers that want a predictable string for development without a
  Groq key.
* `mock=False` — real Groq Chat Completions call using `settings.groq_model`.
"""

from __future__ import annotations

from typing import Any

from src.config import settings


SYSTEM_PROMPT = (
    "You are an on-call SRE assistant. Given a numerical anomaly and the "
    "matched playbook rule, write ONE concise English paragraph (3-5 sentences) "
    "for an on-call channel. State what happened, when, the metric and value, "
    "the likely cause from the rule, and the suggested next action. "
    "Be factual, no marketing tone, no bullet points."
)


def _format_user_prompt(anomaly: dict[str, Any], rule: dict[str, Any]) -> str:
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


def _mock_report(anomaly: dict[str, Any], rule: dict[str, Any]) -> str:
    return (
        f"[MOCK] Anomaly detected on metric '{anomaly.get('metric')}' at "
        f"{anomaly.get('timestamp')} with value {anomaly.get('value')} "
        f"(status={anomaly.get('status')}). "
        f"Matched playbook: {rule.get('rule_text')} "
        f"Suggested action: {rule.get('suggested_action')}."
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
        completion = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _format_user_prompt(anomaly, rule)},
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content.strip()
