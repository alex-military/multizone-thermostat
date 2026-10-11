"""Util package for dummy Home Assistant."""
import re

def slugify(text: str) -> str:
    text = text.lower().strip()
    return re.sub(r'[\s_]+', '_', re.sub(r'[^\w\s-]', '', text))
