from __future__ import annotations


def parse_hand_history(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []

    return []