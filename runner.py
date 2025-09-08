"""High level runner that glues all components together."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from schema_extractor import extract_form_schema
from infer import infer_type
from generators import generate_value
from assertions import assert_success


async def _fill_page(page, log: Dict[str, Any]):
    schema = await extract_form_schema(page)
    for field in schema.fields:
        field_type = infer_type(field)
        selector = f"{field.tag}[name='{field.name}']"
        if field.tag == "input":
            selector = f"input[name='{field.name}']"

        if field.tag == "select":
            options = await page.eval_on_selector_all(
                selector + " option", "opts => opts.map(o => o.value)"
            )
            field.constraints["options"] = options
        value = generate_value(field_type, field)
        log[field.name] = value
        if value is None:
            continue
        if field.tag == "select":
            await page.select_option(selector, value)
        else:
            try:
                await page.fill(selector, value)
            except Exception:
                # some fields may be read only or hidden; ignore
                pass


async def run(config_path: str = "config/target.json") -> Dict[str, Any]:
    """Execute the demo runner and return log data."""

    with open(config_path) as f:
        config = json.load(f)

    target_url = config["url"]
    host = urlparse(target_url).hostname
    if host not in config.get("allowlist", []):
        raise ValueError(f"Host '{host}' not in allowlist")

    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(target_url)
        await page.screenshot(path=str(artifacts / "before.png"))

        log: Dict[str, Any] = {}
        await _fill_page(page, log)

        # Try to find and click a "Next" button to simulate multi-step forms
        next_btn = await page.query_selector("text=Next")
        if next_btn:
            await next_btn.click()
            await _fill_page(page, log)

        # Submit
        submit = await page.query_selector("text=Submit")
        if not submit:
            submit = await page.query_selector("input[type=submit]")
        if submit:
            await submit.click()

        await assert_success(page, config.get("assertions", {}))
        await page.screenshot(path=str(artifacts / "after.png"))

        with open(artifacts / "log.json", "w") as f:
            json.dump(log, f, indent=2)

        await context.close()
        await browser.close()
        return log


if __name__ == "__main__":
    asyncio.run(run())
