"""Util package for dummy Home Assistant."""
from __future__ import annotations

import re
import unicodedata

CYRILLIC_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "iu", "я": "ia",
    "і": "i", "ї": "i", "є": "ie", "ў": "u",
}


def transliterate(text: str) -> str:
    """Transliterate Cyrillic and unicode characters to ASCII."""
    res = []
    for c in text:
        lower_c = c.lower()
        if lower_c in CYRILLIC_MAP:
            res.append(CYRILLIC_MAP[lower_c])
        else:
            res.append(c)
    text = "".join(res)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def slugify(text: str | None, separator: str = "_") -> str:
    """Slugify text according to Home Assistant rules."""
    if not text:
        return ""
    text = transliterate(str(text))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", separator, text)
    return text.strip(separator)
