import asyncio
from google.adk.agents import Agent
from browser.manager import BrowserManager
import os
from dotenv import load_dotenv

load_dotenv()

# Wrapper tools for the browser manager
async def navigate_to_url(url: str) -> str:
    """Navigates the browser to the specified URL."""
    manager = await BrowserManager.get_instance()
    return await manager.navigate(url)

async def click_element(selector: str) -> str:
    """Clicks an element identified by the CSS selector."""
    manager = await BrowserManager.get_instance()
    return await manager.click(selector)

async def type_into_element(selector: str, text: str) -> str:
    """Types text into an element identified by the CSS selector."""
    manager = await BrowserManager.get_instance()
    return await manager.type_text(selector, text)

async def read_page_content() -> str:
    """Returns the visible text content of the current page."""
    manager = await BrowserManager.get_instance()
    return await manager.get_page_content()

async def get_current_url() -> str:
    """Returns the current URL of the page."""
    manager = await BrowserManager.get_instance()
    return await manager.get_current_url()

async def take_screenshot() -> str:
    """Takes a screenshot of the current page for visual confirmation."""
    manager = await BrowserManager.get_instance()
    return await manager.screenshot()

# Define the ADK Agent
def create_web_agent():
    return Agent(
        model='gemini-2.0-flash-exp', # or gemini-1.5-flash
        name='web_agent',
        description="An autonomous web browsing assistant.",
        instruction=(
            "You are a highly capable autonomous web agent. Your goal is to browse the web, "
            "interact with websites, and perform tasks as requested by the user. "
            "Use the provided browser tools to navigate, click, and read information. "
            "Always think step-by-step. If a task is complex, break it down into smaller actions. "
            "If you need to find an element, use CSS selectors. If you are stuck, "
            "use 'read_page_content' to understand the current page state."
        ),
        tools=[
            navigate_to_url,
            click_element,
            type_into_element,
            read_page_content,
            get_current_url,
            take_screenshot
        ],
    )

if __name__ == "__main__":
    # Test script for the agent
    async def test():
        agent = create_web_agent()
        async for event in agent.run_async("Go to google.com and search for 'latest AI news'."):
            print(event)

    asyncio.run(test())
