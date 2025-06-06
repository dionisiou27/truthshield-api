from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # ADD THIS
from fastapi.staticfiles import StaticFiles  # ADD THIS
from pathlib import Path  # ADD THIS
from pydantic import BaseModel
from src.api.detection import router as detection_router
from src.api.monitoring import router as monitoring_router

app = FastAPI(
    title="🛡️ TruthShield API",
    description="European AI Solution for Digital Information Integrity",
    version="0.1.0"
)

# ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(detection_router)
app.include_router(monitoring_router)

class HealthResponse(BaseModel):
    status: str
    message: str
    version: str

@app.get("/")
async def root():
    return {
        "message": "🛡️ TruthShield API - European Digital Shield",
        "features": [
            "🔍 AI Content Detection",
            "📱 Social Media Monitoring", 
            "🏢 Enterprise Protection",
            "🇪🇺 EU Compliance Ready"
        ],
        "endpoints": {
            "detection": "/api/v1/detect/",
            "monitoring": "/api/v1/monitor/",
            "docs": "/docs",
            "demo": "/demo"  # ADD THIS
        }
    }

# ADD THIS NEW ROUTE FOR THE HTML DEMO
@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Serve the HTML demo page"""
    html_path = Path(__file__).parent.parent / "templates" / "index.html"
    
    # Read the HTML file
    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()
    
    # Update the API base URL for production
    html_content = html_content.replace(
        "const API_BASE = 'http://localhost:8000';",
        "const API_BASE = 'https://truthshield-api.onrender.com';"
    )
    
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="TruthShield API is running - All systems operational",
        version="0.1.0"
    )