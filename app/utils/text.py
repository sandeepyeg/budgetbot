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
