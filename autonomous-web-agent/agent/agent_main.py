import asyncio
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
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

# Ensure models have the "models/" prefix
def format_model_id(model_id: str) -> str:
    if not model_id.startswith("models/"):
        return f"models/{model_id}"
    return model_id

# Define the ADK Agent
def create_web_agent():
    model_id = os.getenv("LLM_MODEL_ID", "gemini-3-flash-preview")
    return Agent(
        model=model_id,
        name='web_agent',
        description="An autonomous web browsing assistant.",
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                thinking_level="MEDIUM"
            )
        ),
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
    from google.adk import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    # Test script for the agent
    async def test():
        agent = create_web_agent()
        session_service = InMemorySessionService()
        await session_service.create_session(app_name="web_agent_app", user_id="test_user", session_id="test_session")
        runner = Runner(agent=agent, app_name="web_agent_app", session_service=session_service)
        message = types.Content(role="user", parts=[types.Part(text="Go to google.com")])
        async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=message):
            print(event)

    asyncio.run(test())
