import uvicorn
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    if os.getenv("GOOGLE_API_KEY") == "YOUR_GOOGLE_API_KEY_HERE":
        print("Please set your GOOGLE_API_KEY in the .env file.")
    else:
        print("Starting Autonomous Web Agent Server...")
        uvicorn.run("server.main_app:app", host="0.0.0.0", port=8000, reload=True)
