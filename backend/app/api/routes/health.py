from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import os
from app.core.config import settings

router = APIRouter()

@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    """Simple health check used by Render."""
    return {"status": "ok"}

@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check – ensure DB, Cloudinary config, and upload folder are ready."""
    results = {}
    # DB check
    from app.database.db import engine
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        results["database"] = {"status": "ready"}
    except Exception as e:
        results["database"] = {"status": "error", "detail": str(e)}
    # Cloudinary config check
    cloud_cfg = {
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "api_key": os.getenv("CLOUDINARY_API_KEY"),
        "api_secret": os.getenv("CLOUDINARY_API_SECRET"),
    }
    missing = [k for k, v in cloud_cfg.items() if not v]
    if missing:
        results["cloudinary"] = {"status": "error", "missing": missing}
    else:
        results["cloudinary"] = {"status": "ready"}
    # Upload folder writability check
    try:
        test_path = settings.UPLOAD_FOLDER / "health_test.tmp"
        with open(test_path, "w") as f:
            f.write("test")
        test_path.unlink()
        results["upload_folder"] = {"status": "ready"}
    except Exception as e:
        results["upload_folder"] = {"status": "error", "detail": str(e)}
    overall_status = "ready" if all(v["status"] == "ready" for v in results.values()) else "error"
    return JSONResponse(content={"status": overall_status, "checks": results})
