import pytest


@pytest.mark.integration
def test_upload_documents_returns_created_and_document_ids(client, monkeypatch):
    called = {}

    def fake_add(documents, metadatas, ids):
        called["documents"] = documents
        called["metadatas"] = metadatas
        called["ids"] = ids
        return {"status": "success", "message": "Added 2 documents", "document_ids": ["a", "b"]}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.add_documents", fake_add)

    response = client.post(
        "/api/documents/upload",
        json={"documents": ["doc1", "doc2"], "metadatas": [{}, {}], "ids": ["a", "b"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["document_ids"] == ["a", "b"]
    assert called["documents"] == ["doc1", "doc2"]


@pytest.mark.integration
def test_query_documents_returns_results_from_service(client, monkeypatch):
    def fake_query(query_text, n_results, where):
        assert query_text == "coding"
        assert n_results == 3
        assert where == {"subject": "stem"}
        return {
            "status": "success",
            "query": query_text,
            "results": [{"id": "x", "document": "doc", "similarity": 0.8}],
            "count": 1,
        }

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.query_documents", fake_query)

    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "n_results": 3, "where": {"subject": "stem"}},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["count"] == 1
