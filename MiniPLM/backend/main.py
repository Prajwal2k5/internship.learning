
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend import models

# Import API routers
from backend.routers.parts import router as parts_router
from backend.routers.documents import router as documents_router


# Initialize database tables
Base.metadata.create_all(bind=engine)


# Create FastAPI application
app = FastAPI(
    title="MiniPLM API",
    description="AI-Powered Part and Document Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Configure frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(parts_router)
app.include_router(documents_router)


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to MiniPLM API",
        "status": "running"
    }


# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }
