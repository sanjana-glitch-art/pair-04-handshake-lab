from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
PICTURE_DIR = UPLOAD_DIR / "pictures"
PICTURE_DIR.mkdir(parents=True, exist_ok=True)

MAX_PICTURE_SIZE = 2 * 1024 * 1024

# File signatures, so a renamed non-image is rejected.
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
}


async def save_profile_picture(picture: UploadFile) -> str:
    """
    Validates and stores a PNG or JPEG profile picture.

    Returns the relative path stored in the database. Pictures are
    served publicly from /uploads/pictures; resumes are not.
    """

    contents = await picture.read()

    if len(contents) > MAX_PICTURE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile picture must be smaller than 2 MB.",
        )

    extension = next(
        (
            suffix
            for signature, suffix in IMAGE_SIGNATURES.items()
            if contents.startswith(signature)
        ),
        None,
    )

    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile picture must be a PNG or JPEG image.",
        )

    filename = f"{uuid4().hex}{extension}"
    (PICTURE_DIR / filename).write_bytes(contents)

    return f"uploads/pictures/{filename}"


def remove_upload(relative_path: str | None) -> None:
    """
    Deletes a previously stored upload, ignoring missing files.
    """

    if not relative_path:
        return

    path = (BASE_DIR / relative_path).resolve()

    if UPLOAD_DIR.resolve() in path.parents and path.is_file():
        path.unlink()
