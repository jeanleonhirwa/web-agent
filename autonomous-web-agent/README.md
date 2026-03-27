# Autonomous Web Agent

This is a fully autonomous web agent built using Google's Agent Development Kit (ADK), Gemini Live Model API, and Playwright. It can perform multi-step web tasks and interact with users via text or voice.

## Features
- **Autonomous Browsing:** Uses Playwright to interact with websites.
- **Gemini Live Integration:** Low-latency text and voice interaction.
- **Visual Feedback:** Real-time browser viewport preview in the web interface.
- **Clean UI:** Modern, personalized dashboard.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure API Key:**
   - Open `.env` and replace `YOUR_GOOGLE_API_KEY_HERE` with your actual Google Gemini API key.

3. **Run the Application:**
   ```bash
   python run.py
   ```

4. **Access the Interface:**
   - Open your browser and go to `http://localhost:8000`.

## How it works
- The **Frontend** connects to the **FastAPI Backend** via WebSockets.
- The Backend bridges the user to the **Gemini Live API** for conversation and the **ADK Agent** for task execution.
- The **ADK Agent** uses **Playwright** tools to perform actions on the web and returns summaries of its work.
- The Backend takes periodic screenshots of the browser and sends them to the frontend for visual confirmation.

## Project Structure
- `agent/`: ADK agent definition and tools.
- `browser/`: Playwright-based browser manager.
- `server/`: FastAPI server and WebSocket handler.
- `web/`: Frontend templates and static assets.
