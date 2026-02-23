# Load environment variables FIRST, before any other imports
import os
from dotenv import load_dotenv
load_dotenv()

import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

# Startup validation
if not settings.openai_api_key:
    logger.warning("OPENAI_API_KEY not set — AI features disabled")
if settings.disable_ssl_verify:
    if settings.environment.lower() != "development":
        logger.error("DISABLE_SSL_VERIFY=true ignored outside development")
    else:
        logger.warning("SSL verification disabled — DEVELOPMENT ONLY")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

# Determine paths at module load
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_PATH = PROJECT_ROOT / "docs"
IMAGES_PATH = DOCS_PATH / "images"

# Fallback to CWD if needed
if not IMAGES_PATH.exists():
    IMAGES_PATH = Path(os.getcwd()) / "docs" / "images"
    DOCS_PATH = Path(os.getcwd()) / "docs"

print(f"📁 Images path: {IMAGES_PATH} (exists: {IMAGES_PATH.exists()})")
if IMAGES_PATH.exists():
    print(f"📁 Images found: {list(IMAGES_PATH.glob('*.png'))}")

from src.api.detection import router as detection_router
from src.api.monitoring import router as monitoring_router
from src.api.content import router as content_router
from src.api.compliance import router as compliance_router
from src.api.ml import router as ml_router
from src.api.ml_feedback import router as ml_feedback_router
from src.core.database import init_database

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

_cors_origins = ["*"] if settings.environment.lower() == "development" else origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
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
app.include_router(ml_feedback_router)


@app.on_event("startup")
async def startup():
    await init_database()


# Explicit image route (more reliable than StaticFiles mount on some platforms)
@app.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve images from docs/images folder"""
    image_file = IMAGES_PATH / filename
    if image_file.exists() and image_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']:
        media_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp'
        }
        return FileResponse(image_file, media_type=media_types.get(image_file.suffix.lower(), 'image/png'))
    return Response(status_code=404, content=f"Image not found: {filename}")

# Debug endpoints — only available in development
if settings.environment.lower() == "development":
    @app.get("/debug/paths")
    async def debug_paths():
        """Debug endpoint to check file paths (dev only)"""
        images = list(IMAGES_PATH.glob('*.png')) if IMAGES_PATH.exists() else []
        return {
            "project_root": str(PROJECT_ROOT),
            "docs_path": str(DOCS_PATH),
            "images_path": str(IMAGES_PATH),
            "docs_exists": DOCS_PATH.exists(),
            "images_exists": IMAGES_PATH.exists(),
            "cwd": os.getcwd(),
            "images_found": [img.name for img in images]
        }

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

if settings.environment.lower() == "development":
    @app.get("/debug/env")
    async def debug_environment():
        """Debug endpoint to check if environment variables are loaded (dev only)"""
        return {
            "openai_key_exists": bool(settings.openai_api_key),
            "google_key_exists": bool(settings.google_api_key),
            "news_key_exists": bool(settings.news_api_key),
        }

@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to prevent 404 errors"""
    return Response(status_code=204)  # No Content