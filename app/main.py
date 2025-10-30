from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.routes import router
from app.cache import db as cache_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initialize resources on startup, cleanup on shutdown.
    """
    # Startup
    print("Initializing Restaurant Menu Summarizer...")
    cache_db.init_db()
    print("Database initialized successfully")
    
    yield
    
    # Shutdown
    print("Shutting down Restaurant Menu Summarizer...")

app = FastAPI(
    title="Restaurant Menu Summarizer",
    description="API for extracting and summarizing Czech restaurant menus",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "Restaurant Menu Summarizer",
        "version": "1.0.0",
        "endpoints": {
            "summarize": "POST /summarize",
            "health": "GET /health",
            "cache_stats": "GET /cache/stats"
        }
    }
