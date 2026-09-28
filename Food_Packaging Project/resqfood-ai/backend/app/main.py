"""
ResQFood AI — FastAPI Application Entry Point
"Predict. Prevent. Allocate. Rescue."
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.api import auth, users, demand, surplus, requests, allocation, delivery, analytics, whatsapp

# Create all tables
Base.metadata.create_all(bind=engine)

# Auto-seed if empty (e.g. initial launch on Vercel serverless)
try:
    from app.database import SessionLocal
    from app.models.models import User
    db = SessionLocal()
    if db.query(User).count() == 0:
        from seed.seed_data import seed
        seed()
    db.close()
except Exception as e:
    print(f"Auto-seed check note: {e}")

app = FastAPI(
    title="ResQFood AI",
    description="AI-powered food waste prevention and redistribution platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(demand.router)
app.include_router(surplus.router)
app.include_router(requests.router)
app.include_router(allocation.router)
app.include_router(delivery.router)
app.include_router(analytics.router)
app.include_router(whatsapp.router)


@app.get("/")
def root():
    return {
        "name": "ResQFood AI",
        "tagline": "Predict. Prevent. Allocate. Rescue.",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
