"""High level runner that glues all components together."""

from __future__ import annotations

import asyncio
import json
import random
import re
import string
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

import rstr
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


async def _handle_errors(page, log: Dict[str, Any]) -> bool:
    """Fix form fields based on red error messages.

    Returns ``True`` if any field value was changed.
    """

    error_texts = await page.eval_on_selector_all(
        "body *",
        "els => els.filter(e => getComputedStyle(e).color === 'rgb(255, 0, 0)').map(e => e.textContent)",
    )
    changed = False
    for text in error_texts:
        if not text:
            continue
        msg = text.strip()
        if not msg:
            continue
        field_name = None
        value = None
        if "must match" in msg:
            parts = msg.split("must match", 1)
            field_name = parts[0].strip().lower().replace(" ", "_")
            pattern = parts[1].strip()
            regex = pattern.replace("#", r"\d")
            try:
                value = rstr.xeger(regex)
            except Exception:
                continue
        elif "must be at most" in msg and "characters" in msg:
            m = re.match(r"(.+?)\s+must be at most\s+(\d+)\s+characters", msg)
            if m:
                field_name = m.group(1).strip().lower().replace(" ", "_")
                num = int(m.group(2))
                value = rstr.xeger(r"[A-Za-z]{%d}" % num)
        elif "must be" in msg and "digits" in msg:
            m = re.match(r"(.+?)\s+must be\s+(\d+)\s+digits", msg)
            if m:
                field_name = m.group(1).strip().lower().replace(" ", "_")
                num = int(m.group(2))
                value = "".join(random.choice(string.digits) for _ in range(num))
        if field_name and value is not None:
            selector = f"input[name='{field_name}']"
            try:
                await page.fill(selector, value)
                log[field_name] = value
                changed = True
            except Exception:
                pass
    return changed


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

        # Submit and handle validation errors
        submit = await page.query_selector("text=Submit")
        if not submit:
            submit = await page.query_selector("input[type=submit]")
        attempts = 0
        while submit and attempts < 2:
            await submit.click()
            changed = await _handle_errors(page, log)
            if not changed:
                break
            submit = await page.query_selector("text=Submit")
            if not submit:
                submit = await page.query_selector("input[type=submit]")
            attempts += 1

        await assert_success(page, config.get("assertions", {}))
        await page.screenshot(path=str(artifacts / "after.png"))

        with open(artifacts / "log.json", "w") as f:
            json.dump(log, f, indent=2)

        await context.close()
        await browser.close()
        return log


if __name__ == "__main__":
    asyncio.run(run())
