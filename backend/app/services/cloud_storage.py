import os
try:
    import cloudinary
    import cloudinary.uploader
    from cloudinary.utils import cloudinary_url
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False

if CLOUDINARY_AVAILABLE:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

def upload_file(file_bytes: bytes, filename: str) -> str:
    """Upload a file and return a URL.

    If Cloudinary is configured and available, the file is uploaded to Cloudinary.
    Otherwise, the file is saved locally under a 'uploads' directory and a file URL is returned.
    """
    if CLOUDINARY_AVAILABLE and all([os.getenv("CLOUDINARY_CLOUD_NAME"), os.getenv("CLOUDINARY_API_KEY"), os.getenv("CLOUDINARY_API_SECRET")]):
        result = cloudinary.uploader.upload(file_bytes, public_id=filename, resource_type="raw")
        return result.get("secure_url")
    else:
        # Fallback to local storage
        upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        # Return a file URL path (could be served statically later)
        return f"file://{os.path.abspath(file_path)}"

def get_file_url(public_id: str) -> str:
    """Retrieve the URL for an already uploaded asset.
    """
    url, _ = cloudinary_url(public_id, resource_type="raw", secure=True)
    return url
