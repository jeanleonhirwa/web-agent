import os
import asyncio
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from google import genai
from agent.agent_main import create_web_agent
from browser.manager import BrowserManager
import json
import base64

load_dotenv()

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.0-flash-exp")

# Initialize the ADK Web Agent
web_agent = create_web_agent()

@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")
    
    try:
        # Establish connection with Gemini Live API
        config = {"response_modalities": ["AUDIO", "TEXT"]}
        
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            print("Connected to Gemini Live.")
            
            # Start a background task to listen for Gemini Live responses and forward to client
            async def listen_from_gemini():
                async for message in session:
                    # Forward Gemini Live response (audio/text) to our frontend
                    if message.server_content is not None:
                        # Extract text if present
                        model_turn = message.server_content.model_turn
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                if part.text:
                                    await websocket.send_text(json.dumps({
                                        "type": "text",
                                        "content": part.text
                                    }))
                                if part.inline_data:
                                    # Send raw audio data as base64
                                    audio_base64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    await websocket.send_text(json.dumps({
                                        "type": "audio",
                                        "content": audio_base64
                                    }))

            gemini_listener = asyncio.create_task(listen_from_gemini())

            # Listen for messages from our frontend
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message["type"] == "user_text":
                    user_input = message["content"]
                    
                    # 1. Run the autonomous agent
                    agent_response = ""
                    async for event in web_agent.run_async(user_input):
                        # You can also stream events back to frontend if needed
                        if hasattr(event, "content"):
                            agent_response += str(event.content)
                        elif isinstance(event, str):
                            agent_response += event
                    
                    # 2. Inform the Live API about the agent's work
                    await session.send(input=f"The web agent performed the following actions: {agent_response}. Respond to the user about it.", end_of_turn=True)
                    
                    # 3. Update the frontend with the agent's summary
                    await websocket.send_text(json.dumps({
                        "type": "agent_log",
                        "content": agent_response
                    }))
                    
                    # 4. Take a screenshot for the user to see
                    manager = await BrowserManager.get_instance()
                    screenshot_path = await manager.screenshot("browser_preview.png")
                    await websocket.send_text(json.dumps({
                        "type": "screenshot",
                        "url": "/static/browser_preview.png"
                    }))

                elif message["type"] == "user_audio":
                    # Send raw audio to Gemini Live session
                    audio_data = base64.b64decode(message["content"])
                    await session.send(input={
                        "mime_type": "audio/pcm;rate=16000",
                        "data": audio_data
                    })

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup if needed
        pass

@app.on_event("shutdown")
async def shutdown_event():
    manager = await BrowserManager.get_instance()
    await manager.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
