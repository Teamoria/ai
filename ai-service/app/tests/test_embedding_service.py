"""Embedding service tests."""

from types import SimpleNamespace
import sys

from app.core.config import settings
from app.services.embedding_service import EmbeddingService


def test_embedding_service_local_fallback_dimensions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_provider", "local")
    monkeypatch.setattr(settings, "embedding_dimensions", 8)

    vector = EmbeddingService().embed("Teamoria knowledge")

    assert len(vector) == 8
    assert all(-1 <= value <= 1 for value in vector)


def test_embedding_service_uses_openai_when_configured(monkeypatch) -> None:
    calls = {}

    class FakeEmbeddings:
        def create(self, *, model, input, dimensions):
            calls["model"] = model
            calls["input"] = input
            calls["dimensions"] = dimensions
            return SimpleNamespace(
                data=[
                    SimpleNamespace(
                        embedding=[0.25, 0.5, 0.75],
                    )
                ]
            )

    class FakeOpenAI:
        def __init__(self, *, api_key):
            calls["api_key"] = api_key
            self.embeddings = FakeEmbeddings()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(settings, "embedding_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")

    vector = EmbeddingService().embed("Contract parties", dimensions=5)

    assert calls == {
        "api_key": "test-key",
        "model": "text-embedding-3-small",
        "input": "Contract parties",
        "dimensions": 5,
    }
    assert vector == [0.25, 0.5, 0.75, 0.0, 0.0]
