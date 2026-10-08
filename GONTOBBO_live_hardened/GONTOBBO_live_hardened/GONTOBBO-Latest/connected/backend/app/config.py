import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file located at backend root or current directory
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings:
    """Application configuration settings."""

    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "").strip()
    HOST: str = os.getenv("HOST", "0.0.0.0").strip()
    PORT: int = int(os.getenv("PORT", "8000").strip() or "8000")
    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30.0"))
    SERPAPI_BASE_URL: str = "https://serpapi.com/search"


settings = Settings()
