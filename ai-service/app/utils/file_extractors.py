"""File text extraction helpers."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status


TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".srt", ".vtt", ".log"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
MEDIA_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".mov", ".avi", ".mkv"}


@dataclass(frozen=True)
class UploadSource:
    source_type: str
    text: str | None = None
    path: Path | None = None
    source: str = "content"


def resolve_upload_source(
    *,
    content: str | None = None,
    file_path: str | None = None,
    file_url: str | None = None,
) -> UploadSource:
    if content:
        return UploadSource(source_type="text", text=content, source="content")

    if file_path:
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="file_path does not exist or is not a file.",
            )

        return _source_from_path(path, source=file_path)

    if file_url:
        return _source_from_url(file_url)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Provide content, file_path, or file_url for processing.",
    )


def extract_text_from_source(
    *,
    content: str | None = None,
    file_path: str | None = None,
    file_url: str | None = None,
) -> str:
    """Extract text from raw content, a local path, or a URL.

    Laravel should prefer sending raw text when it already extracted it. For local
    demos this also supports plain text-like files. Binary document parsing can be
    added later without changing the API contract.
    """

    source = resolve_upload_source(content=content, file_path=file_path, file_url=file_url)

    if source.text is not None:
        return source.text

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"{source.source_type} uploads require a dedicated processor.",
    )


def _source_from_path(path: Path, *, source: str) -> UploadSource:
    suffix = path.suffix.lower()

    if suffix in MEDIA_EXTENSIONS:
        return UploadSource(source_type="media", path=path, source=source)

    if suffix in DOCUMENT_EXTENSIONS:
        return UploadSource(source_type=suffix.removeprefix("."), text=_read_document(path), source=source)

    if suffix in TEXT_EXTENSIONS or suffix == "":
        return UploadSource(source_type="text", text=path.read_text(encoding="utf-8", errors="ignore"), source=source)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported upload file type: {suffix}",
    )


def _source_from_url(file_url: str) -> UploadSource:
    path = _download_url(file_url)
    return _source_from_path(path, source=file_url)


def _download_url(file_url: str) -> Path:
    suffix = Path(urlparse(file_url).path).suffix
    request = Request(file_url, headers={"User-Agent": "Teamoria-AI-Service/1.0"})

    try:
        with urlopen(request, timeout=20) as response:
            with NamedTemporaryFile(delete=False, suffix=suffix or ".upload") as temp_file:
                temp_file.write(response.read())
                return Path(temp_file.name)
    except (OSError, URLError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to read file_url: {exc}",
        ) from exc


def _read_document(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Install pypdf to process PDF uploads.",
            ) from exc

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Install python-docx to process DOCX uploads.",
            ) from exc

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported document type: {suffix}",
    )
