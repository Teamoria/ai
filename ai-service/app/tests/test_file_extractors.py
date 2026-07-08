"""File extractor tests."""

from types import SimpleNamespace
import sys

from app.core.config import settings
from app.utils import file_extractors


def test_image_tesseract_extracts_english_text_when_available(tmp_path) -> None:
    tesseract_cmd = file_extractors.Path(settings.tesseract_cmd)
    if not tesseract_cmd.exists():
        return

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (800, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 60), "Teamoria Contract 500 USD", fill="black")
    image_path = tmp_path / "ocr.png"
    image.save(image_path)

    source = file_extractors.resolve_upload_source(file_path=str(image_path))

    assert source.source_type == "image"
    assert "Teamoria" in source.text


def test_image_openai_vision_fallback_extracts_text(tmp_path, monkeypatch) -> None:
    calls = {}

    class FakeCompletions:
        def create(self, *, model, messages, temperature):
            calls["model"] = model
            calls["temperature"] = temperature
            calls["has_image"] = messages[1]["content"][0]["type"] == "image_url"
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Party A: Teamoria LLC"),
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    image_path = tmp_path / "contract.png"
    image_path.write_bytes(b"fake-image")

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_vision_model", "gpt-4o-mini")

    text = file_extractors._read_image_with_openai_vision(image_path)

    assert text == "Party A: Teamoria LLC"
    assert calls == {
        "api_key": "test-key",
        "model": "gpt-4o-mini",
        "temperature": 0,
        "has_image": True,
    }
