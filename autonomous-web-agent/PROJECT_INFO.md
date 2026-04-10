# Project: Autonomous Web Agent

## Vision
An autonomous web agent capable of performing complex multi-step tasks in a browser, just like a human. Users can interact via text or voice through a clean, personalized web interface powered by the Gemini Live Model API.

## Core Features
- **Browser Automation:** Fully autonomous navigation, clicking, typing, and information extraction.
- **Multimodal Interaction:** Supports real-time text and voice interaction using Gemini Live.
- **Task Durability:** Handles tasks ranging from single actions to 10-minute multi-step workflows.
- **Clean Interface:** A personalized web dashboard for task management and interaction.

## Tech Stack
- **Agent Framework:** Google Agent Development Kit (ADK) for Python.
- **LLM Brain:** Google Gemini 3 Flash (`gemini-3-flash-preview`).
- **Live Model:** Google Gemini 3.1 Flash Live (`gemini-3.1-flash-live-preview`).
- **Browser Automation:** Playwright (Python).
- **Backend:** FastAPI (Python) for bridging the frontend to the Gemini Live API and ADK agent.
- **Frontend:** Vanilla HTML, CSS (clean aesthetic), and JavaScript.

## Architecture
- **Agent Orchestration:** Uses the `google.adk.Runner` for managing agent interactions.
- **Session Management:** Employs `google.adk.sessions.InMemorySessionService` to maintain context across a user session.
- **Async Workflow:** Fully asynchronous communication between the Frontend, FastAPI, Gemini Live API, and the ADK Agent.
- **Event Handling:** The agent streams `Event` objects which are processed to extract `Content` parts (text and reasoning).

## User's Initial prompt to  build this app
Build me an Autonomous web agent that can do anything that a human can do in browser or on web. Make it able to do small things like a single action or task/tasks/activities that can take like 10 minutes or several actions, Make it fully autonomous. User can interact it with text or voice using gemini live model api. Build it in python with google's adk(agent development kit) but with a clean personalized website for interacting with it. and also create an md file and save all information about this project, so next time you or any ai coding agent will have context of the project to continue building effectively. Start building 💪

## Next Steps
1. Initialize the Python environment and install dependencies.
2. Implement the Playwright-based browser tool for the ADK agent.
3. Configure the ADK agent with the browser tool.
4. Build the FastAPI backend and integrate Gemini Live.
5. Create the frontend interface.
