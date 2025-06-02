import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "TruthShield API is starting...", "port": os.environ.get("PORT", "8000")}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Try to import the real app
try:
    from src.api.main import app as real_app
    app = real_app
    print("Successfully loaded TruthShield API")
except Exception as e:
    print(f"Error loading main app: {e}")
    print("Running fallback API")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
