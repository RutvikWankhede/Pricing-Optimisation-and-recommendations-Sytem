import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Initialise Cloudinary configuration from environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

def upload_file(file_bytes: bytes, filename: str) -> str:
    """Upload a file to Cloudinary and return the secure URL.

    This wrapper handles missing Cloudinary configuration gracefully.
    If required environment variables are not set, a RuntimeError is raised
    and the caller can decide how to proceed (e.g., fallback to local storage).
    """
    # Verify Cloudinary configuration
    if not all([os.getenv("CLOUDINARY_CLOUD_NAME"), os.getenv("CLOUDINARY_API_KEY"), os.getenv("CLOUDINARY_API_SECRET")]):
        raise RuntimeError("Cloudinary environment variables not configured")
    result = cloudinary.uploader.upload(file_bytes, public_id=filename, resource_type="raw")
    return result.get("secure_url")
    """Upload a file to Cloudinary and return the secure URL.

    Parameters
    ----------
    file_bytes: bytes
        The raw file content.
    filename: str
        Original filename (used for public_id).
    Returns
    -------
    str
        Secure URL of the uploaded asset.
    """
    result = cloudinary.uploader.upload(file_bytes, public_id=filename, resource_type="raw")
    return result.get("secure_url")

def get_file_url(public_id: str) -> str:
    """Retrieve the URL for an already uploaded asset.
    """
    url, _ = cloudinary_url(public_id, resource_type="raw", secure=True)
    return url
