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
    
    # Database configuration
    # Determine environment (default to development)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Upload size limits
    MAX_IMAGE_SIZE: int = int(os.getenv("MAX_IMAGE_SIZE", "5242880"))  # 5 MB
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", "26214400"))  # 25 MB

    # Database URL handling
    _db_url: str | None = os.getenv("DATABASE_URL")
    if ENVIRONMENT == "production":
        if not _db_url:
            raise RuntimeError("DATABASE_URL environment variable is required for production.")
        DATABASE_URL: str = _db_url
    else:
        # Development fallback to SQLite file in BASE_DIR
        DATABASE_URL = _db_url or f"sqlite:///{BASE_DIR / 'dev.db'}"

    # JWT Security configuration
    _secret_key: str | None = os.getenv("SECRET_KEY")
    if ENVIRONMENT == "production":
        if not _secret_key:
            raise RuntimeError("SECRET_KEY environment variable is required for security in production")
        SECRET_KEY: str = _secret_key
    else:
        # Development placeholder secret
        SECRET_KEY = _secret_key or "dev-secret-key"
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
