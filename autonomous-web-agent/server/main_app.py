import os
import asyncio
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from google import genai
from google.genai import types
from agent.agent_main import create_web_agent, format_model_id
from browser.manager import BrowserManager
import json
import base64
import traceback
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

load_dotenv()

app = FastAPI()

# Ensure static directory exists
os.makedirs("web/static", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Initialize Gemini Client
client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY"),
    http_options=types.HttpOptions(api_version='v1beta')
)

LIVE_MODEL_ID = format_model_id(os.getenv("LIVE_MODEL_ID", "gemini-3.1-flash-live-preview"))

# Initialize the ADK Web Agent, Session Service and Runner
web_agent = create_web_agent()
session_service = InMemorySessionService()
agent_runner = Runner(agent=web_agent, app_name="web_agent_app", session_service=session_service)


@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


async def run_agent_task(user_input: str, user_id: str, session_id: str, websocket: WebSocket):
    """Run the ADK agent and return its response with retry logic."""
    agent_response = ""
    message = types.Content(role="user", parts=[types.Part(text=user_input)])
    max_retries = 3

    # Send a "thinking" indicator
    await websocket.send_text(json.dumps({
        "type": "status",
        "content": "thinking"
    }))

    for attempt in range(max_retries):
        try:
            agent_response = ""
            async for event in agent_runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message
            ):
                # Extract content from events
                if hasattr(event, "content") and event.content:
                    if hasattr(event.content, "parts") and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                agent_response += part.text
                    elif isinstance(event.content, str):
                        agent_response += event.content
            # Success - break out of retry loop
            break
        except Exception as e:
            error_str = str(e)
            is_retryable = "429" in error_str or "503" in error_str or "UNAVAILABLE" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if is_retryable and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)  # 2, 4, 8 seconds
                print(f"API error (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s: {e}")
                await websocket.send_text(json.dumps({
                    "type": "agent_log",
                    "content": f"⏳ API busy, retrying in {wait_time}s... (attempt {attempt+1}/{max_retries})"
                }))
                await asyncio.sleep(wait_time)
            else:
                agent_response = f"Agent error: {e}"
                print(f"Agent execution error: {e}")
                traceback.print_exc()
                break

    # Send agent log to frontend
    if agent_response:
        await websocket.send_text(json.dumps({
            "type": "agent_log",
            "content": agent_response
        }))

    # Take a screenshot and send it
    try:
        manager = await BrowserManager.get_instance()
        await manager.screenshot("browser_preview.png")
        await websocket.send_text(json.dumps({
            "type": "screenshot",
            "url": "/static/browser_preview.png"
        }))
    except Exception as e:
        print(f"Screenshot error: {e}")

    # Send done indicator
    await websocket.send_text(json.dumps({
        "type": "status",
        "content": "done"
    }))

    return agent_response


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")

    # Create a unique session for this WebSocket connection
    user_id = "web_user"
    session_id = f"session_{id(websocket)}"
    await session_service.create_session(
        app_name="web_agent_app", user_id=user_id, session_id=session_id
    )

    # Try to connect Gemini Live in background (optional enhancement)
    live_session = None
    gemini_listener = None

    try:
        # Attempt to connect Gemini Live API (non-blocking)
        try:
            config = types.LiveConnectConfig(
                response_modalities=["TEXT"],
            )
            print(f"Attempting Gemini Live connection: {LIVE_MODEL_ID}...")
            live_connection = client.aio.live.connect(model=LIVE_MODEL_ID, config=config)
            live_session = await live_connection.__aenter__()
            print("Gemini Live connected successfully!")

            # Start background listener for Gemini Live responses
            async def listen_from_gemini():
                try:
                    async for message in live_session.receive():
                        if message.server_content is not None:
                            model_turn = message.server_content.model_turn
                            if model_turn and model_turn.parts:
                                for part in model_turn.parts:
                                    if part.text:
                                        await websocket.send_text(json.dumps({
                                            "type": "text",
                                            "content": part.text
                                        }))
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Gemini listener error: {e}")

            gemini_listener = asyncio.create_task(listen_from_gemini())

        except Exception as e:
            print(f"Gemini Live unavailable (will use text-only mode): {e}")
            live_session = None

        # Notify frontend about mode
        mode = "live" if live_session else "text-only"
        if mode == "text-only":
            await websocket.send_text(json.dumps({
                "type": "text",
                "content": "⚡ Connected! I'll browse the web and complete your tasks."
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "text",
                "content": "🎙️ Connected with voice support! I'll browse the web and complete your tasks."
            }))

        # Main message loop
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "user_text":
                user_input = msg["content"]

                # Run the agent task
                agent_response = await run_agent_task(
                    user_input, user_id, session_id, websocket
                )

                if live_session:
                    # Feed agent result to Gemini Live for conversational response
                    try:
                        await live_session.send(
                            input=f"The web agent performed: {agent_response}. Summarize for the user.",
                            end_of_turn=True
                        )
                    except Exception as e:
                        print(f"Live send error: {e}")
                        # Fallback: send as plain text
                        await websocket.send_text(json.dumps({
                            "type": "text",
                            "content": agent_response
                        }))
                else:
                    # Text-only mode: send agent response directly
                    if agent_response:
                        await websocket.send_text(json.dumps({
                            "type": "text",
                            "content": agent_response
                        }))

            elif msg["type"] == "user_audio":
                if live_session:
                    try:
                        audio_data = base64.b64decode(msg["content"])
                        await live_session.send(input={
                            "mime_type": "audio/pcm;rate=16000",
                            "data": audio_data
                        })
                    except Exception as e:
                        print(f"Audio send error: {e}")

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if gemini_listener:
            gemini_listener.cancel()
        if live_session:
            try:
                await live_connection.__aexit__(None, None, None)
            except Exception:
                pass
        print("WebSocket session ended.")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        manager = await BrowserManager.get_instance()
        await manager.close()
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
