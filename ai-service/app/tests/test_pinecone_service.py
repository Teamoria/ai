"""Pinecone service helper tests."""

from app.services.pinecone_service import _search_filter, _source_metadata


def test_search_filter_includes_optional_scope_fields() -> None:
    assert _search_filter(
        project_id="project-1",
        company_id="company-1",
        scope="project",
        visibility="members",
    ) == {
        "$and": [
            {"project_id": {"$eq": "project-1"}},
            {"company_id": {"$eq": "company-1"}},
            {"scope": {"$eq": "project"}},
            {"visibility": {"$eq": "members"}},
        ]
    }


def test_source_metadata_adds_source_id_and_snippet() -> None:
    metadata = _source_metadata(
        {
            "upload_id": "upload-1",
            "chunk_index": 3,
            "text": "A" * 600,
        }
    )

    assert metadata["source_id"] == "upload-1:3"
    assert metadata["snippet"] == "A" * 500
