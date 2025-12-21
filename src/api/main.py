from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from src.api.detection import router as detection_router
from src.api.monitoring import router as monitoring_router
from src.api.content import router as content_router
from src.api.compliance import router as compliance_router
from src.api.ml import router as ml_router

app = FastAPI(
    title="🛡️ TruthShield API",
    description="European AI Solution for Digital Information Integrity",
    version="0.1.0"
)

# CORS MIDDLEWARE
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://dionisiou27.github.io",
    "https://truthshield-demo.surge.sh",
    "null",  # Allow file:// URLs for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(detection_router)
app.include_router(monitoring_router)
app.include_router(content_router)
app.include_router(compliance_router)
app.include_router(ml_router)

# Serve static files (images, css, etc.) from docs folder
# Try multiple path resolution methods for compatibility
import os
project_root = Path(__file__).resolve().parent.parent.parent
docs_path = project_root / "docs"
images_path = docs_path / "images"

# Fallback: try CWD-based path if the above doesn't work
if not images_path.exists():
    cwd_images = Path(os.getcwd()) / "docs" / "images"
    if cwd_images.exists():
        images_path = cwd_images
        docs_path = Path(os.getcwd()) / "docs"

print(f"📁 Project root: {project_root}")
print(f"📁 Docs path: {docs_path} (exists: {docs_path.exists()})")
print(f"📁 Images path: {images_path} (exists: {images_path.exists()})")
if images_path.exists():
    app.mount("/images", StaticFiles(directory=str(images_path)), name="images")
else:
    print(f"⚠️ Images folder not found at {images_path}")

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
            "content": "/api/v1/content/",
            "compliance": "/api/v1/compliance/",
            "ml": "/api/v1/ml/",
            "docs": "/docs",
            "demo": "/demo"
        }
    }

# HTML DEMO ROUTE
@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Serve the HTML demo page"""
    # Read the demo HTML file
    demo_file = Path(__file__).parent.parent.parent / "docs" / "index.html"
    if demo_file.exists():
        with open(demo_file, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="""
        <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🛡️ TruthShield Demo</h1>
                <p>Demo file not found. Please check the docs/index.html file.</p>
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

@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check if environment variables are loaded"""
    import os
    return {
        "openai_key_exists": bool(os.getenv("OPENAI_API_KEY")),
        "google_key_exists": bool(os.getenv("GOOGLE_API_KEY")),
        "news_key_exists": bool(os.getenv("NEWS_API_KEY")),
        "debug_info": "Check if environment variables are loaded on Render"
    }

@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to prevent 404 errors"""
    return Response(status_code=204)  # No Content