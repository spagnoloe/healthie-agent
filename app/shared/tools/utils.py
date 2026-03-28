"""Shared utilities for Healthie EHR integration."""

import os

from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

_browser: Browser | None = None
_page: Page | None = None


async def login_to_healthie() -> Page:
    """Log into Healthie and return an authenticated page instance.

    This function handles the login process using credentials from environment
    variables. The browser and page instances are stored for reuse by other
    functions in this module.

    Returns:
        Page: An authenticated Playwright Page instance ready for use.

    Raises:
        ValueError: If required environment variables are missing.
        Exception: If login fails for any reason.
    """
    global _browser, _page

    email = os.environ.get("HEALTHIE_EMAIL")
    password = os.environ.get("HEALTHIE_PASSWORD")

    if not email or not password:
        raise ValueError("HEALTHIE_EMAIL and HEALTHIE_PASSWORD must be set in environment variables")

    if _page is not None:
        logger.info("Using existing Healthie session")
        return _page

    logger.info("Logging into Healthie...")
    playwright = await async_playwright().start()
    _browser = await playwright.chromium.launch(headless=True)
    _page = await _browser.new_page()

    await _page.goto("https://secure.gethealthie.com/users/sign_in", wait_until="domcontentloaded")

    # Wait for the email input to be visible
    email_input = _page.locator('input[name="email"]')
    await email_input.wait_for(state="visible", timeout=30000)
    await email_input.fill(email)

    # Wait for password input
    password_input = _page.locator('input[name="password"]')
    await password_input.wait_for(state="visible", timeout=30000)
    await password_input.fill(password)

    # Find and click the Log In button
    submit_button = _page.locator('button:has-text("Log In")')
    await submit_button.wait_for(state="visible", timeout=30000)
    await submit_button.click()

    # Wait for navigation after login
    await _page.wait_for_timeout(3000)

    # Check if we've navigated away from the sign-in page
    current_url = _page.url
    if "sign_in" in current_url:
        raise Exception("Login may have failed - still on sign-in page")

    logger.info("Successfully logged into Healthie")
    return _page
