from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pathlib import Path
from pydantic import BaseModel
from src.api.detection import router as detection_router
from src.api.monitoring import router as monitoring_router

app = FastAPI(
    title="🛡️ TruthShield API",
    description="European AI Solution for Digital Information Integrity",
    version="0.1.0"
)

# CORS MIDDLEWARE
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
            "demo": "/demo"
        }
    }

# HTML DEMO ROUTE
@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Serve the HTML demo page"""
    # For now, return a simple message
    # You'll need to add your HTML file to the project
    return HTMLResponse(content="""
    <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🛡️ TruthShield Demo</h1>
            <p>Please upload the demo.html file to your project.</p>
            <p>Visit <a href="/docs">API Documentation</a></p>
        </body>
    </html>
    """)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="TruthShield API is running - All systems operational",
        version="0.1.0"
    )