from contextlib import asynccontextmanager
import logging
import os
import secrets
import sqlite3
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes.travel import router as travel_router
from app.models.travel import ErrorDetail, ErrorResponse
from app.services.serpapi_client import close_http_client

from app.db import create_db_and_tables
from app.api.routes.auth import router as auth_router

# Load the private backend/.env when running Uvicorn directly. The startup
# shell may export these values, but local and hosted previews often do not.
#ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
#load_dotenv(ENV_FILE, override=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gontobbo.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager to clean up HTTP client connections."""
    logger.info("Starting GONTOBBO Travel Backend service...")
    yield
    await create_db_and_tables()
    yield
    logger.info("Shutting down GONTOBBO Travel Backend service...")
    await close_http_client()


app = FastAPI(
    title="GONTOBBO Travel Backend API",
    description="Clean, modular travel search service for flights and hotels powered by SerpApi.",
    version="1.0.0",
    lifespan=lifespan,
    telemetry={"auto_configure": False},
)

# Permit the bundled frontend when opened through file:// or a local
# static server such as VS Code Live Server. No cookies are used by these
# API calls, so wildcard origins are safe for this local distribution.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register API routes
app.include_router(auth_router)
app.include_router(travel_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format request validation errors into GONTOBBO standard error envelope."""
    error_messages = []
    for err in exc.errors():
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        error_messages.append(f"{field_path}: {msg}")

    detail_message = "; ".join(error_messages) or "Validation failed for request parameters."

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(code="VALIDATION_ERROR", message=detail_message),
        ).model_dump(),
    )


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
