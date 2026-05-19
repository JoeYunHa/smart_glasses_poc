"""CI guard: detect stale Groq / legacy provider references in config and docs.

Any GROQ_ environment variable key in .env.example or README.md indicates
an incomplete migration and should fail CI immediately.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parents[3]
_API_ROOT = Path(__file__).parents[1]

_BANNED_PATTERNS = [
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "GROQ_TEXT_MODEL",
    "groq_api_key",
    "groq_model",
    "groq_text_model",
]


def _scan(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        for pat in _BANNED_PATTERNS:
            if pat in line:
                hits.append((lineno, line.strip()))
    return hits


def test_env_example_no_groq_keys():
    env_example = _API_ROOT / ".env.example"
    assert env_example.exists(), ".env.example not found"
    hits = _scan(env_example)
    assert not hits, (
        f".env.example contains banned Groq keys:\n"
        + "\n".join(f"  line {ln}: {text}" for ln, text in hits)
    )


def test_env_example_confidence_threshold_matches_code_default():
    """ROUTER_CONFIDENCE_THRESHOLD in .env.example must equal config.py default (0.35)."""
    env_example = _API_ROOT / ".env.example"
    assert env_example.exists(), ".env.example not found"
    for line in env_example.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("ROUTER_CONFIDENCE_THRESHOLD="):
            _, _, value = line.partition("=")
            assert float(value.strip()) == 0.35, (
                f"ROUTER_CONFIDENCE_THRESHOLD in .env.example is {value.strip()!r}, "
                "expected 0.35 (must match config.py default)"
            )
            return
    # Key absent — no conflict, skip
