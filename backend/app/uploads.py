"""
Uploaded files live in MongoDB GridFS, not on a container's disk, so
every replica of every service sees the same files.

- pictures bucket: profile pictures, served publicly at
  /uploads/pictures/{filename}
- resumes bucket: PDF resumes, only reachable through the company's
  authorized preview endpoint

Stored paths keep the Lab 1 shape ("uploads/pictures/<name>.png",
"uploads/<name>.pdf"), so the React app did not have to change.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from gridfs.errors import NoFile

from .database import picture_bucket, resume_bucket


MAX_PICTURE_SIZE = 2 * 1024 * 1024
MAX_RESUME_SIZE = 5 * 1024 * 1024

# File signatures, so a renamed non-image is rejected.
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": (".png", "image/png"),
    b"\xff\xd8\xff": (".jpg", "image/jpeg"),
}


async def save_profile_picture(picture: UploadFile) -> str:
    contents = await picture.read()

    if len(contents) > MAX_PICTURE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile picture must be smaller than 2 MB.")

    match = next(
        (info for signature, info in IMAGE_SIGNATURES.items() if contents.startswith(signature)),
        None,
    )

    if match is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile picture must be a PNG or JPEG image.")

    extension, content_type = match
    filename = f"{uuid4().hex}{extension}"
    picture_bucket().upload_from_stream(filename, contents, metadata={"contentType": content_type})

    return f"uploads/pictures/{filename}"


def validate_resume(filename: str | None, contents: bytes) -> None:
    if not (filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF resumes are allowed.")
    if len(contents) > MAX_RESUME_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume file must be smaller than 5 MB.")
    if not contents.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a valid PDF.")


def store_resume(contents: bytes, original_name: str | None, owner_id: int) -> str:
    filename = f"{uuid4().hex}.pdf"
    resume_bucket().upload_from_stream(
        filename,
        contents,
        metadata={"contentType": "application/pdf", "original_name": original_name, "owner_id": owner_id},
    )
    return f"uploads/{filename}"


def read_resume(resume_path: str) -> bytes | None:
    try:
        return resume_bucket().open_download_stream_by_name(resume_path.rsplit("/", 1)[-1]).read()
    except NoFile:
        return None


def remove_upload(relative_path: str | None) -> None:
    """
    Deletes a stored picture or resume, ignoring missing files.
    """

    if not relative_path:
        return

    name = relative_path.rsplit("/", 1)[-1]
    bucket = picture_bucket() if "/pictures/" in relative_path else resume_bucket()

    for stored in bucket.find({"filename": name}):
        bucket.delete(stored._id)


pictures_router = APIRouter(tags=["Uploads"])


@pictures_router.get("/uploads/pictures/{filename}", include_in_schema=False)
def get_picture(filename: str):
    try:
        stream = picture_bucket().open_download_stream_by_name(filename)
    except NoFile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picture not found.")

    content_type = (stream.metadata or {}).get("contentType", "application/octet-stream")
    return Response(
        content=stream.read(),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
