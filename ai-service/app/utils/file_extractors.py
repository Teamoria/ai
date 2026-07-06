"""File text extraction helpers."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
import re
import unicodedata
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
        return UploadSource(source_type="text", text=clean_extracted_text(content), source="content")

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
        return UploadSource(source_type="text", text=clean_extracted_text(path.read_text(encoding="utf-8", errors="ignore")), source=source)

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
        text = _read_pdf_with_pypdf(path)
        if _is_low_quality_text(text):
            fallback_text = _read_pdf_with_pymupdf(path)
            if fallback_text and _text_quality_score(fallback_text) > _text_quality_score(text):
                text = fallback_text
        return clean_extracted_text(text)

    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Install python-docx to process DOCX uploads.",
            ) from exc

        document = Document(str(path))
        return clean_extracted_text("\n".join(paragraph.text for paragraph in document.paragraphs))

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unsupported document type: {suffix}",
    )


def clean_extracted_text(text: str) -> str:
    """Normalize extracted/transcribed text before AI analysis and persistence."""

    return _clean_extracted_text(text)


def _read_pdf_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Install pypdf to process PDF uploads.",
        ) from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _read_pdf_with_pymupdf(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""

    with fitz.open(str(path)) as document:
        return "\n".join(page.get_text("text") or "" for page in document).strip()


def _clean_extracted_text(text: str) -> str:
    candidate = _maybe_fix_mojibake(text)
    candidate = unicodedata.normalize("NFKC", candidate)
    candidate = candidate.replace("\u200f", " ").replace("\u200e", " ")
    candidate = re.sub(r"[ \t]+", " ", candidate)
    candidate = re.sub(r"\n{3,}", "\n\n", candidate)
    return candidate.strip()


def _maybe_fix_mojibake(text: str) -> str:
    if not text:
        return ""

    try:
        candidate = text.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
    except UnicodeError:
        return text

    if _arabic_char_count(candidate) > _arabic_char_count(text) and len(candidate) > len(text) * 0.35:
        return candidate

    return text


def _is_low_quality_text(text: str) -> bool:
    clean_text = text.strip()
    if len(clean_text) < 40:
        return True
    return _text_quality_score(clean_text) < 0


def _text_quality_score(text: str) -> int:
    return _arabic_char_count(_clean_without_mojibake_retry(text)) - _mojibake_marker_count(text) * 3


def _clean_without_mojibake_retry(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def _arabic_char_count(text: str) -> int:
    return sum(1 for char in text if "\u0600" <= char <= "\u06ff")


def _mojibake_marker_count(text: str) -> int:
    return sum(text.count(marker) for marker in ("Ø", "Ù", "ï", "�"))
