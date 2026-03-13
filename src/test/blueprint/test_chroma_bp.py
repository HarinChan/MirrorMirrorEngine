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
def test_upload_documents_missing_documents_field_returns_400(client):
    response = client.post(
        "/api/documents/upload",
        json={"ids": ["a"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "Missing 'documents' field"


@pytest.mark.integration
@pytest.mark.parametrize("documents", ["doc1", [], None])
def test_upload_documents_invalid_documents_returns_400(client, documents):
    response = client.post(
        "/api/documents/upload",
        json={"documents": documents},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'documents' must be a non-empty list"


@pytest.mark.integration
def test_upload_documents_service_error_returns_500(client, monkeypatch):
    def fake_add(documents, metadatas, ids):
        return {"status": "error", "message": "failed"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.add_documents", fake_add)

    response = client.post(
        "/api/documents/upload",
        json={"documents": ["doc1"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload == {"status": "error", "message": "failed"}


@pytest.mark.integration
def test_upload_documents_service_exception_returns_500(client, monkeypatch):
    def fake_add(documents, metadatas, ids):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.add_documents", fake_add)

    response = client.post(
        "/api/documents/upload",
        json={"documents": ["doc1"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "boom"


@pytest.mark.integration
def test_query_documents_returns_results_from_service(client, monkeypatch):
    def fake_query(query_text, n_results, where, min_similarity):
        assert query_text == "coding"
        assert n_results == 3
        assert where == {"subject": "stem"}
        assert min_similarity is None
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


@pytest.mark.integration
def test_query_documents_forwards_min_similarity_to_service(client, monkeypatch):
    called = {}

    def fake_query(query_text, n_results, where, min_similarity):
        called["query_text"] = query_text
        called["n_results"] = n_results
        called["where"] = where
        called["min_similarity"] = min_similarity
        return {"status": "success", "results": [], "count": 0}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.query_documents", fake_query)

    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "n_results": 2, "where": {"subject": "stem"}, "min_similarity": 0.75},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert called == {
        "query_text": "coding",
        "n_results": 2,
        "where": {"subject": "stem"},
        "min_similarity": 0.75,
    }


@pytest.mark.integration
def test_query_documents_missing_query_returns_400(client):
    response = client.post(
        "/api/documents/query",
        json={"n_results": 5},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "Missing 'query' field"


@pytest.mark.integration
@pytest.mark.parametrize("query", ["", "   ", 42, None])
def test_query_documents_invalid_query_returns_400(client, query):
    response = client.post(
        "/api/documents/query",
        json={"query": query},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'query' must be a non-empty string"


@pytest.mark.integration
@pytest.mark.parametrize("n_results", [0, -1, "5", None])
def test_query_documents_invalid_n_results_returns_400(client, n_results):
    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "n_results": n_results},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'n_results' must be a positive integer"


@pytest.mark.integration
def test_query_documents_invalid_where_type_returns_400(client):
    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "where": ["not", "a", "dict"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'where' must be an object when provided"


@pytest.mark.integration
@pytest.mark.parametrize("min_similarity", ["0.5", {"x": 1}, [0.5]])
def test_query_documents_non_numeric_min_similarity_returns_400(client, min_similarity):
    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "min_similarity": min_similarity},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'min_similarity' must be a number between 0 and 1"


@pytest.mark.integration
@pytest.mark.parametrize("min_similarity", [-0.01, 1.01])
def test_query_documents_out_of_range_min_similarity_returns_400(client, min_similarity):
    response = client.post(
        "/api/documents/query",
        json={"query": "coding", "min_similarity": min_similarity},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'min_similarity' must be between 0 and 1"


@pytest.mark.integration
def test_query_documents_service_error_returns_500(client, monkeypatch):
    def fake_query(query_text, n_results, where, min_similarity):
        return {"status": "error", "message": "query failed"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.query_documents", fake_query)

    response = client.post(
        "/api/documents/query",
        json={"query": "coding"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json() == {"status": "error", "message": "query failed"}


@pytest.mark.integration
def test_query_documents_service_exception_returns_500(client, monkeypatch):
    def fake_query(query_text, n_results, where, min_similarity):
        raise RuntimeError("query explode")

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.query_documents", fake_query)

    response = client.post(
        "/api/documents/query",
        json={"query": "coding"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "query explode"


@pytest.mark.integration
def test_delete_documents_returns_200_on_success(client, monkeypatch):
    called = {}

    def fake_delete(ids):
        called["ids"] = ids
        return {"status": "success", "message": "deleted"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.delete_documents", fake_delete)

    response = client.delete(
        "/api/documents/delete",
        json={"ids": ["a", "b"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json() == {"status": "success", "message": "deleted"}
    assert called["ids"] == ["a", "b"]


@pytest.mark.integration
def test_delete_documents_missing_ids_returns_400(client):
    response = client.delete(
        "/api/documents/delete",
        json={"foo": "bar"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "Missing 'ids' field"


@pytest.mark.integration
@pytest.mark.parametrize("ids", ["a", [], None])
def test_delete_documents_invalid_ids_returns_400(client, ids):
    response = client.delete(
        "/api/documents/delete",
        json={"ids": ids},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "'ids' must be a non-empty list"


@pytest.mark.integration
def test_delete_documents_service_error_returns_500(client, monkeypatch):
    def fake_delete(ids):
        return {"status": "error", "message": "delete failed"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.delete_documents", fake_delete)

    response = client.delete(
        "/api/documents/delete",
        json={"ids": ["a"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json() == {"status": "error", "message": "delete failed"}


@pytest.mark.integration
def test_delete_documents_service_exception_returns_500(client, monkeypatch):
    def fake_delete(ids):
        raise RuntimeError("delete explode")

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.delete_documents", fake_delete)

    response = client.delete(
        "/api/documents/delete",
        json={"ids": ["a"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "delete explode"


@pytest.mark.integration
def test_get_collection_info_returns_200_on_success(client, monkeypatch):
    def fake_info():
        return {"status": "success", "count": 3}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.get_collection_info", fake_info)

    response = client.get("/api/documents/info")

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json() == {"status": "success", "count": 3}


@pytest.mark.integration
def test_get_collection_info_service_error_returns_500(client, monkeypatch):
    def fake_info():
        return {"status": "error", "message": "info failed"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.get_collection_info", fake_info)

    response = client.get("/api/documents/info")

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json() == {"status": "error", "message": "info failed"}


@pytest.mark.integration
def test_get_collection_info_service_exception_returns_500(client, monkeypatch):
    def fake_info():
        raise RuntimeError("info explode")

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.get_collection_info", fake_info)

    response = client.get("/api/documents/info")

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "info explode"


@pytest.mark.integration
def test_update_document_returns_200_on_success(client, monkeypatch):
    called = {}

    def fake_update(document_id, document, metadata):
        called["document_id"] = document_id
        called["document"] = document
        called["metadata"] = metadata
        return {"status": "success", "message": "updated"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.update_document", fake_update)

    response = client.put(
        "/api/documents/update",
        json={"id": "a", "document": "new text", "metadata": {"subject": "stem"}},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json() == {"status": "success", "message": "updated"}
    assert called == {"document_id": "a", "document": "new text", "metadata": {"subject": "stem"}}


@pytest.mark.integration
@pytest.mark.parametrize("payload", [{"id": "a"}, {"document": "text"}, {}])
def test_update_document_missing_required_fields_returns_400(client, payload):
    response = client.put(
        "/api/documents/update",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    result = response.get_json()
    assert result["status"] == "error"
    assert result["message"] == "Missing 'id' or 'document' field"


@pytest.mark.integration
@pytest.mark.parametrize("document_id", ["", "   ", 1, None])
def test_update_document_invalid_id_returns_400(client, document_id):
    response = client.put(
        "/api/documents/update",
        json={"id": document_id, "document": "text"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    result = response.get_json()
    assert result["status"] == "error"
    assert result["message"] == "'id' must be a non-empty string"


@pytest.mark.integration
@pytest.mark.parametrize("document", ["", "   ", 1, None])
def test_update_document_invalid_document_returns_400(client, document):
    response = client.put(
        "/api/documents/update",
        json={"id": "a", "document": document},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400, response.get_data(as_text=True)
    result = response.get_json()
    assert result["status"] == "error"
    assert result["message"] == "'document' must be a non-empty string"


@pytest.mark.integration
def test_update_document_service_error_returns_500(client, monkeypatch):
    def fake_update(document_id, document, metadata):
        return {"status": "error", "message": "update failed"}

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.update_document", fake_update)

    response = client.put(
        "/api/documents/update",
        json={"id": "a", "document": "text"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    assert response.get_json() == {"status": "error", "message": "update failed"}


@pytest.mark.integration
def test_update_document_service_exception_returns_500(client, monkeypatch):
    def fake_update(document_id, document, metadata):
        raise RuntimeError("update explode")

    monkeypatch.setattr("src.app.blueprint.chroma_bp.chroma_service.update_document", fake_update)

    response = client.put(
        "/api/documents/update",
        json={"id": "a", "document": "text"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 500, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload["status"] == "error"
    assert payload["message"] == "update explode"
