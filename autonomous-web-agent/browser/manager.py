import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os

class BrowserManager:
    _instance = None
    _lock = asyncio.Lock()
    _playwright = None
    _browser: Browser = None
    _context: BrowserContext = None
    _page: Page = None
    _initialized = False

    @classmethod
    async def get_instance(cls):
        if cls._initialized and cls._instance is not None:
            return cls._instance

        async with cls._lock:
            # Double-check after acquiring lock
            if cls._initialized and cls._instance is not None:
                return cls._instance

            try:
                print("Launching Playwright browser...")
                cls._playwright = await async_playwright().start()
                cls._browser = await cls._playwright.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ]
                )
                cls._context = await cls._browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                cls._page = await cls._context.new_page()
                cls._instance = BrowserManager()
                cls._initialized = True
                print("Browser launched successfully!")
            except Exception as e:
                print(f"FATAL: Failed to launch browser: {e}")
                # Clean up partial state
                cls._instance = None
                cls._initialized = False
                if cls._browser:
                    try:
                        await cls._browser.close()
                    except Exception:
                        pass
                if cls._playwright:
                    try:
                        await cls._playwright.stop()
                    except Exception:
                        pass
                cls._playwright = None
                cls._browser = None
                cls._context = None
                cls._page = None
                raise RuntimeError(f"Failed to launch browser: {e}") from e

        return cls._instance

    async def navigate(self, url: str):
        """Navigates the browser to the specified URL."""
        if self._page is None:
            raise RuntimeError("Browser page not initialized")
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return f"Navigated to {url}"
        except Exception as e:
            return f"Navigation error for {url}: {e}"

    async def click(self, selector: str):
        """Clicks an element identified by the CSS selector."""
        if self._page is None:
            raise RuntimeError("Browser page not initialized")
        try:
            await self._page.click(selector, timeout=10000)
            await self._page.wait_for_load_state("domcontentloaded")
            return f"Clicked element: {selector}"
        except Exception as e:
            return f"Click error for {selector}: {e}"

    async def type_text(self, selector: str, text: str):
        """Types text into an element identified by the CSS selector."""
        if self._page is None:
            raise RuntimeError("Browser page not initialized")
        try:
            await self._page.fill(selector, text)
            return f"Typed '{text}' into {selector}"
        except Exception as e:
            return f"Type error for {selector}: {e}"

    async def get_page_content(self):
        """Returns the current page's HTML content (simplified as text)."""
        if self._page is None:
            raise RuntimeError("Browser page not initialized")
        try:
            content = await self._page.evaluate("() => document.body.innerText")
            return content[:5000]  # Limit to avoid context overflow
        except Exception as e:
            return f"Read error: {e}"

    async def get_current_url(self):
        """Returns the current URL of the page."""
        if self._page is None:
            return "about:blank"
        return self._page.url

    async def screenshot(self, filename: str = "screenshot.png"):
        """Takes a screenshot of the current page."""
        if self._page is None:
            return "No browser page to screenshot"
        try:
            path = os.path.join("web", "static", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            await self._page.screenshot(path=path)
            return f"Screenshot saved to {path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    async def close(self):
        """Closes the browser and stops Playwright."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        BrowserManager._instance = None
        BrowserManager._initialized = False
        BrowserManager._playwright = None
        BrowserManager._browser = None
        BrowserManager._context = None
        BrowserManager._page = None
