from types import SimpleNamespace

import pytest

import src.app.service.chromadb_service as chroma_module


class FakeCollection:
	def __init__(self):
		self.add_calls = []
		self.update_calls = []
		self.delete_calls = []
		self.count_value = 0
		self.query_result = {
			"ids": [["a", "b"]],
			"documents": [["doc a", "doc b"]],
			"metadatas": [[{"k": "v"}, {"k": "v2"}]],
			"distances": [[0.1, 0.4]],
		}

	def add(self, documents, metadatas, ids):
		self.add_calls.append({"documents": documents, "metadatas": metadatas, "ids": ids})

	def query(self, query_texts, n_results, where, include):
		return self.query_result

	def delete(self, ids):
		self.delete_calls.append(ids)

	def count(self):
		return self.count_value

	def update(self, **kwargs):
		self.update_calls.append(kwargs)


@pytest.fixture
def service_with_fake_collection(monkeypatch):
	fake_collection = FakeCollection()

	class FakeClient:
		def get_or_create_collection(self, name, metadata):
			return fake_collection

	monkeypatch.setattr(chroma_module.chromadb, "PersistentClient", lambda path: FakeClient())
	service = chroma_module.ChromaDBService(persist_directory="/tmp/chroma-test", collection_name="test")
	return service, fake_collection


def test_add_documents_generates_ids_and_defaults_metadata(service_with_fake_collection, monkeypatch):
	service, fake_collection = service_with_fake_collection
	monkeypatch.setattr(chroma_module.uuid, "uuid4", lambda: "generated-id")

	result = service.add_documents(["doc"])

	assert result["status"] == "success"
	assert result["document_ids"] == ["generated-id"]
	assert fake_collection.add_calls[0]["metadatas"] == [{}]


def test_add_documents_returns_error_on_exception(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection

	def boom(documents, metadatas, ids):
		raise RuntimeError("add failed")

	fake_collection.add = boom
	result = service.add_documents(["doc"], metadatas=[{}], ids=["x"])
	assert result == {"status": "error", "message": "add failed"}


def test_query_documents_formats_similarity_and_applies_threshold(service_with_fake_collection):
	service, _ = service_with_fake_collection

	result = service.query_documents("hello", n_results=2, min_similarity=0.7)

	assert result["status"] == "success"
	assert result["count"] == 1
	assert result["results"][0]["id"] == "a"
	assert result["results"][0]["similarity"] == 0.9


def test_query_documents_returns_error_on_exception(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection

	def boom(query_texts, n_results, where, include):
		raise RuntimeError("query failed")

	fake_collection.query = boom
	result = service.query_documents("hello")
	assert result == {"status": "error", "message": "query failed"}


def test_delete_documents_success_and_error(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection

	success = service.delete_documents(["a", "b"])
	assert success["status"] == "success"
	assert success["deleted_ids"] == ["a", "b"]

	def boom(ids):
		raise RuntimeError("delete failed")

	fake_collection.delete = boom
	error = service.delete_documents(["a"])
	assert error == {"status": "error", "message": "delete failed"}


def test_get_collection_info_success_and_error(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection
	fake_collection.count_value = 7

	success = service.get_collection_info()
	assert success == {"status": "success", "collection_name": "test", "document_count": 7}

	def boom():
		raise RuntimeError("count failed")

	fake_collection.count = boom
	error = service.get_collection_info()
	assert error == {"status": "error", "message": "count failed"}


def test_update_document_with_and_without_metadata(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection

	with_meta = service.update_document("doc-1", "new", {"source": "x"})
	assert with_meta["status"] == "success"
	assert fake_collection.update_calls[0]["metadatas"] == [{"source": "x"}]

	without_meta = service.update_document("doc-2", "newer")
	assert without_meta["status"] == "success"
	assert "metadatas" not in fake_collection.update_calls[1]


def test_update_document_returns_error_on_exception(service_with_fake_collection):
	service, fake_collection = service_with_fake_collection

	def boom(**kwargs):
		raise RuntimeError("update failed")

	fake_collection.update = boom
	result = service.update_document("doc-1", "new")
	assert result == {"status": "error", "message": "update failed"}