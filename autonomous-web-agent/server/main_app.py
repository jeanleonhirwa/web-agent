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

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Initialize Gemini Client with explicit v1beta
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")
    
    # Create a unique session for this WebSocket connection
    user_id = "web_user"
    session_id = f"session_{id(websocket)}"
    await session_service.create_session(app_name="web_agent_app", user_id=user_id, session_id=session_id)
    
    try:
        # Establish connection with Gemini Live API
        config = {
            "response_modalities": ["AUDIO", "TEXT"],
            "generation_config": {
                "thinking_config": {
                    "thinking_level": "MINIMAL"
                }
            }
        }
        
        print(f"Connecting to Gemini Live: {LIVE_MODEL_ID}...")
        
        async with client.aio.live.connect(model=LIVE_MODEL_ID, config=config) as session:
            print(f"Connected to Gemini Live session.")
            
            # Start a background task to listen for Gemini Live responses
            async def listen_from_gemini():
                try:
                    async for message in session.receive():
                        if message.server_content is not None:
                            model_turn = message.server_content.model_turn
                            if model_turn and model_turn.parts:
                                for part in model_turn.parts:
                                    if part.text:
                                        await websocket.send_text(json.dumps({
                                            "type": "text",
                                            "content": part.text
                                        }))
                                    if part.inline_data:
                                        audio_base64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                                        await websocket.send_text(json.dumps({
                                            "type": "audio",
                                            "content": audio_base64
                                        }))
                except Exception as inner_e:
                    print(f"Gemini Listener Error: {inner_e}")

            gemini_listener = asyncio.create_task(listen_from_gemini())

            # Listen for messages from our frontend
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                
                if msg["type"] == "user_text":
                    user_input = msg["content"]
                    
                    # 1. Run the autonomous agent via Runner
                    agent_response = ""
                    # Runner requires a Content object
                    message = types.Content(role="user", parts=[types.Part(text=user_input)])
                    
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
                    
                    # 2. Inform the Live API about the agent's work
                    await session.send(input=f"The web agent performed the following actions: {agent_response}. Respond to the user about it.", end_of_turn=True)
                    
                    # 3. Update the frontend with the agent's summary
                    await websocket.send_text(json.dumps({
                        "type": "agent_log",
                        "content": agent_response
                    }))
                    
                    # 4. Take a screenshot
                    manager = await BrowserManager.get_instance()
                    await manager.screenshot("browser_preview.png")
                    await websocket.send_text(json.dumps({
                        "type": "screenshot",
                        "url": "/static/browser_preview.png"
                    }))

                elif msg["type"] == "user_audio":
                    audio_data = base64.b64decode(msg["content"])
                    await session.send(input={
                        "mime_type": "audio/pcm;rate=16000",
                        "data": audio_data
                    })

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        traceback.print_exc()
    finally:
        pass

@app.on_event("shutdown")
async def shutdown_event():
    manager = await BrowserManager.get_instance()
    await manager.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
