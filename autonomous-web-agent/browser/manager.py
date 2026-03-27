import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os

class BrowserManager:
    _instance = None
    _playwright = None
    _browser: Browser = None
    _context: BrowserContext = None
    _page: Page = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = BrowserManager()
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(headless=False)  # Set to True for production
            cls._context = await cls._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            cls._page = await cls._context.new_page()
        return cls._instance

    async def navigate(self, url: str):
        """Navigates the browser to the specified URL."""
        await self._page.goto(url, wait_until="networkidle")
        return f"Navigated to {url}"

    async def click(self, selector: str):
        """Clicks an element identified by the CSS selector."""
        await self._page.click(selector)
        await self._page.wait_for_load_state("networkidle")
        return f"Clicked element: {selector}"

    async def type_text(self, selector: str, text: str):
        """Types text into an element identified by the CSS selector."""
        await self._page.fill(selector, text)
        return f"Typed '{text}' into {selector}"

    async def get_page_content(self):
        """Returns the current page's HTML content (simplified as text)."""
        content = await self._page.evaluate("() => document.body.innerText")
        return content[:5000] # Limit to avoid context overflow

    async def get_current_url(self):
        """Returns the current URL of the page."""
        return self._page.url

    async def screenshot(self, filename: str = "screenshot.png"):
        """Takes a screenshot of the current page."""
        path = os.path.join("web", "static", filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self._page.screenshot(path=path)
        return f"Screenshot saved to {path}"

    async def close(self):
        """Closes the browser and stops Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        BrowserManager._instance = None
