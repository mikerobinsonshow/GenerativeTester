"""Success assertion helpers."""

from __future__ import annotations

from typing import Dict, Any
from playwright.async_api import Page


async def assert_success(page: Page, config: Dict[str, Any]) -> None:
    """Raise ``AssertionError`` if success conditions are not met."""

    selector = config.get("selector")
    url_contains = config.get("url_contains")

    if selector:
        await page.wait_for_selector(selector, timeout=5000)

    if url_contains:
        assert url_contains in page.url, f"Expected '{url_contains}' in {page.url}"
