from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from dotenv import load_dotenv
import os
from app.utils.logging_config import configure_logging

load_dotenv()

# Configure logging early
configure_logging()

app = FastAPI(title="Excel AI Modifier - Backend (FastAPI)")

# Allow local frontend origin; adjust if needed
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
