from __future__ import annotations

"""Utilities to extract form schema information from a Playwright page.

This module inspects the DOM of the current page and returns a ``FormSchema``
object describing all fields that can be filled.  Only very small pieces of the
real project are implemented – just enough for a proof of concept.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel
from playwright.async_api import Page


class FieldSchema(BaseModel):
    """Representation of a single form field."""

    name: str
    label: Optional[str] = None
    html_type: str
    tag: str
    constraints: Dict[str, str] = {}


class FormSchema(BaseModel):
    """Schema describing all fields on a page."""

    action: Optional[str] = None
    fields: List[FieldSchema] = []


async def _get_label(page: Page, element) -> Optional[str]:
    """Try to find a human friendly label for ``element``.

    The heuristic checks associated ``<label for="id">`` tags, ``aria-label``
    attributes and wrapping ``<label>`` elements.
    """

    element_id = await element.get_attribute("id")
    if element_id:
        label = await page.query_selector(f'label[for="{element_id}"]')
        if label:
            text = await label.inner_text()
            if text:
                return text.strip()

    aria = await element.get_attribute("aria-label")
    if aria:
        return aria.strip()

    # Finally check if element is inside a <label> element
    text = await element.evaluate(
        "el => el.closest('label') ? el.closest('label').textContent : null"
    )
    if text:
        return str(text).strip()
    return None


async def extract_form_schema(page: Page) -> FormSchema:
    """Extract a :class:`FormSchema` from ``page``.

    All ``input``, ``select`` and ``textarea`` elements are inspected.  The
    returned schema intentionally contains only a subset of possible metadata
    but is sufficient for the demo.
    """

    elements = await page.query_selector_all("input, select, textarea")
    fields: List[FieldSchema] = []

    for el in elements:
        tag_name = await el.evaluate("e => e.tagName.toLowerCase()")
        html_type = await el.get_attribute("type") or tag_name
        name = (
            await el.get_attribute("name")
            or await el.get_attribute("id")
            or tag_name
        )
        label = await _get_label(page, el)
        fields.append(
            FieldSchema(name=name, label=label, html_type=html_type, tag=tag_name)
        )

    action = await page.evaluate("document.forms[0] ? document.forms[0].action : null")

    return FormSchema(action=action, fields=fields)
