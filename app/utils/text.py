import re
import unicodedata

def slugify(value: str) -> str:
    """
    Very small, dependency-free slugify. Lowercase, strip accents, keep alnum and hyphens.
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "other"


def short_ref(value: str, size: int = 8) -> str:
    if not value:
        return ""
    return value[:size]


def normalize_merchant(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for suffix in (" inc", " ltd", " llc", " corp", " company", " co"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text.title() if text else "Unknown"


def progress_bar(pct: float, length: int = 10) -> str:
    safe = max(0.0, min(100.0, pct))
    filled = int(round((safe / 100.0) * length))
    return "█" * filled + "░" * (length - filled)
