"""
Launcher script to run the Urban Flood Prediction and Routing backend server directly.
"""
import uvicorn
import sys
import os

# Ensure backend module can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("=================================================================")
    print("🌊 Starting Metro Flood Nowcast & Safe Routing System (FastAPI)")
    print("   API Docs:   http://localhost:8000/docs")
    print("   Health:     http://localhost:8000/api/status")
    print("=================================================================")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
