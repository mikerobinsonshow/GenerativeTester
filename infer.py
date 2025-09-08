"""Simple field type inference heuristics."""

from __future__ import annotations

import re
from typing import Optional
from schema_extractor import FieldSchema


_PATTERNS = {
    "email": re.compile(r"email", re.I),
    "phone": re.compile(r"phone|tel|mobile", re.I),
    "name": re.compile(r"name", re.I),
    "date": re.compile(r"date", re.I),
    "zip": re.compile(r"zip|postal", re.I),
    "password": re.compile(r"password", re.I),
}


def infer_type(field: FieldSchema) -> str:
    """Return the logical type for ``field``.

    The function looks at the HTML ``type`` attribute, the field name and any
    human readable label.  The returned string is used by ``generators`` to
    create appropriate dummy values.
    """

    # direct hints from html type
    type_hint = (field.html_type or "").lower()
    if type_hint in {"email", "tel", "date", "password"}:
        return {
            "tel": "phone",
            "date": "date",
        }.get(type_hint, type_hint)

    # Check name/label with regex patterns
    haystack = " ".join(filter(None, [field.name, field.label]))
    for key, pattern in _PATTERNS.items():
        if pattern.search(haystack):
            return key

    if field.tag == "select":
        return "select"

    return "text"
