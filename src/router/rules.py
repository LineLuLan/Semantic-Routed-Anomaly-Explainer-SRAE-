"""Business rules catalog for SRAE semantic routing.

Source-of-truth list of (rule_text, suggested_action) playbooks. Encoded into
ChromaDB by `src/router/seed_chroma.py` and queried by `SemanticRouter`.

Originally lived in `src/db/seed.py` against pgvector; migrated here as part of
the 2026-04-25 pivot to ChromaDB (see PLAN.md §10).
"""

from __future__ import annotations

BUSINESS_RULES: list[tuple[str, str]] = [
    (
        "High late-night traffic between 1 AM and 4 AM indicates possible bot "
        "scraping or a scheduled crawler hitting the site.",
        "Check firewall logs and enable rate limiting for the affected endpoints.",
    ),
    (
        "A sudden drop in sales during normal business hours signals a broken "
        "checkout, payment gateway failure, or expired promotion.",
        "Inspect the checkout funnel, verify payment provider status, and review "
        "recent deploys.",
    ),
    (
        "A spike in error_rate on API endpoints points to a bad deploy, a "
        "downstream dependency outage, or a database slowdown.",
        "Roll back the latest deploy, page the on-call engineer, and check "
        "dependency dashboards.",
    ),
    (
        "Traffic falling to near zero across all metrics suggests a CDN outage, "
        "DNS failure, or upstream load balancer issue.",
        "Verify CDN status page, run DNS probes from external locations, and "
        "confirm load balancer health checks.",
    ),
    (
        "Sales surging far above forecast without a marketing campaign can mean "
        "pricing is mis-configured or an external viral event is driving demand.",
        "Audit recent pricing changes, confirm stock levels, and prepare "
        "scaling for the surge.",
    ),
    (
        "An elevated error_rate combined with flat traffic implies a backend "
        "regression rather than a user-facing issue.",
        "Inspect application logs, look for recent schema migrations, and verify "
        "background worker health.",
    ),
]
