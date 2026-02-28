import os
import uuid
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {
    "resume": {"pdf", "doc", "docx"},
    "photo": {"jpg", "jpeg", "png"},
    "document": {"pdf", "doc", "docx", "jpg", "jpeg", "png"},
}

MAX_SIZES = {
    "resume": 5 * 1024 * 1024,    # 5 MB
    "photo": 2 * 1024 * 1024,     # 2 MB
    "document": 5 * 1024 * 1024,  # 5 MB
}


def _allowed_file(filename, file_type):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())


def validate_and_save_file(file, file_type, upload_folder):
    """Validate file type/size and save to uploads/<file_type>/.

    Returns the relative path to the saved file, or raises ValueError.
    """
    if not file or file.filename == "":
        raise ValueError("No file provided")

    if not _allowed_file(file.filename, file_type):
        allowed = ", ".join(ALLOWED_EXTENSIONS.get(file_type, []))
        raise ValueError(f"File type not allowed. Accepted: {allowed}")

    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    max_size = MAX_SIZES.get(file_type, 5 * 1024 * 1024)
    if size > max_size:
        raise ValueError(f"File too large. Max size: {max_size // (1024 * 1024)} MB")

    # Build destination
    subdir = os.path.join(upload_folder, file_type)
    os.makedirs(subdir, exist_ok=True)

    # Unique filename to avoid collisions
    ext = file.filename.rsplit(".", 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(subdir, safe_name)
    file.save(dest)

    return f"uploads/{file_type}/{safe_name}"
