import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from backend/.env if present
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "AI Pricing Optimization & Revenue Intelligence System"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    
    # Database
    
    # Upload size limits
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "5242880"))  # 5 MB
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", "26214400"))  # 25 MB
    # Production: PostgreSQL URL required. No fallback to SQLite in production.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL"
    )
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is required for production.")
    
    # JWT Security
    # SECRET_KEY must be provided via environment; no default for production
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is required for security")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "180"))
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    
    # Upload & Report Directories
    UPLOAD_FOLDER: Path = BASE_DIR / "datasets" / "raw"
    PROCESSED_FOLDER: Path = BASE_DIR / "datasets" / "processed"
    REPORT_FOLDER: Path = BASE_DIR / "reports"
    
    def __init__(self):
        # Ensure directories exist
        self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_FOLDER.mkdir(parents=True, exist_ok=True)
        self.REPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        (self.REPORT_FOLDER / "pdf").mkdir(parents=True, exist_ok=True)
        (self.REPORT_FOLDER / "excel").mkdir(parents=True, exist_ok=True)

settings = Settings()
