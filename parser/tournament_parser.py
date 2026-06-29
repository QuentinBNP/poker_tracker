from __future__ import annotations


def parse_tournament_summary(text: str) -> dict[str, str]:
    if not text.strip():
        return {}

    return {}