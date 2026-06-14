"""
Integration tests for TypesenseTagSearchRepo.

The Typesense client is replaced with a lightweight fake so tests never
touch a real search cluster.  The ExpansionWorker's background thread is
patched out to keep tests synchronous and deterministic.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from app.domain_models.tags.tag import Tag
from app.repositories.external.search_engine.typesense_tag_search_repo import TypesenseTagSearchRepo


# ---------------------------------------------------------------------------
# Fake Typesense client
# ---------------------------------------------------------------------------

class FakeDocuments:
    """Minimal stand-in for client.collections[name].documents."""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._search_result: dict = {"hits": []}

    def upsert(self, doc: dict):
        self._store[doc["id"]] = doc

    def search(self, params: dict) -> dict:
        return self._search_result

    def set_search_result(self, hits: list[dict]):
        self._search_result = {"hits": hits}

    def __getitem__(self, doc_id: str):
        return _FakeDocRef(self._store, doc_id)


class _FakeDocRef:
    def __init__(self, store, doc_id):
        self._store = store
        self._doc_id = str(doc_id)  # docs are stored with string keys

    def delete(self):
        if self._doc_id not in self._store:
            raise Exception("not found")
        del self._store[self._doc_id]


class FakeCollection:
    def __init__(self):
        self.documents = FakeDocuments()

    def retrieve(self):
        return {}   # pretend it already exists → skip creation


class FakeCollections:
    def __init__(self):
        self._col = FakeCollection()

    def __getitem__(self, name: str) -> FakeCollection:
        return self._col

    def create(self, schema: dict):
        pass   # no-op


class FakeTypesenseClient:
    def __init__(self):
        self.collections = FakeCollections()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_client():
    return FakeTypesenseClient()


@pytest.fixture()
def repo(fake_client):
    """Repo with background worker neutered so tests stay synchronous."""
    with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker") as MockWorker:
        MockWorker.return_value.enqueue = MagicMock()
        r = TypesenseTagSearchRepo(fake_client)
    return r


def _tag(id: int = 1, name: str = "jazz") -> Tag:
    return Tag(id=id, name=name)


# ---------------------------------------------------------------------------
# add_tag
# ---------------------------------------------------------------------------

class TestAddTag:
    def test_returns_true_on_success(self, repo, fake_client):
        assert repo.add_tag(_tag()) is True

    def test_document_immediately_stored_with_plain_name(self, repo, fake_client):
        tag = _tag(id=42, name="techno")
        repo.add_tag(tag)
        docs = fake_client.collections["tags"].documents._store
        assert "42" in docs
        assert docs["42"]["name"] == "techno"
        assert docs["42"]["embedding_name"] == "techno"

    def test_expansion_worker_is_enqueued(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker") as MockWorker:
            mock_enqueue = MagicMock()
            MockWorker.return_value.enqueue = mock_enqueue
            r = TypesenseTagSearchRepo(fake_client)

        tag = _tag(id=7, name="jazz")
        r.add_tag(tag)
        mock_enqueue.assert_called_once_with(tag)


# ---------------------------------------------------------------------------
# remove_tag
# ---------------------------------------------------------------------------

class TestRemoveTag:
    def test_returns_true_when_document_exists(self, repo, fake_client):
        tag = _tag(id=5, name="rock")
        repo.add_tag(tag)
        assert repo.remove_tag(tag) is True

    def test_document_no_longer_in_store_after_removal(self, repo, fake_client):
        tag = _tag(id=5, name="rock")
        repo.add_tag(tag)
        repo.remove_tag(tag)
        assert "5" not in fake_client.collections["tags"].documents._store

    def test_returns_false_when_document_not_found(self, repo):
        assert repo.remove_tag(_tag(id=999)) is False


# ---------------------------------------------------------------------------
# _process_tag  (the async expansion callback)
# ---------------------------------------------------------------------------

class TestProcessTag:
    def test_upserts_expanded_embedding_name(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        with patch.object(repo.expander, "expand_tag_slow", return_value="swing bebop"):
            repo._process_tag(_tag(id=3, name="jazz"))

        doc = fake_client.collections["tags"].documents._store["3"]
        assert doc["embedding_name"] == "jazz swing bebop"
        assert doc["name"] == "jazz"

    def test_expand_tag_slow_called_with_tag_name(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        with patch.object(repo.expander, "expand_tag_slow", return_value="x") as mock_expand:
            repo._process_tag(_tag(id=1, name="märchen"))

        mock_expand.assert_called_once_with("märchen")


# ---------------------------------------------------------------------------
# search_by_semantic
# ---------------------------------------------------------------------------

class TestSearchBySemantic:
    def test_returns_list_of_tags(self, repo, fake_client):
        fake_client.collections["tags"].documents.set_search_result([
            {"document": {"id": "1", "name": "jazz"}},
            {"document": {"id": "2", "name": "blues"}},
        ])
        results = repo.search_by_semantic("jazz", page=1)
        assert len(results) == 2
        assert all(isinstance(t, Tag) for t in results)

    def test_tag_fields_are_mapped_correctly(self, repo, fake_client):
        fake_client.collections["tags"].documents.set_search_result([
            {"document": {"id": "7", "name": "theater"}},
        ])
        results = repo.search_by_semantic("theater", page=1)
        assert results[0].id == 7
        assert results[0].name == "theater"

    def test_returns_empty_list_on_search_exception(self, repo, fake_client):
        fake_client.collections["tags"].documents.search = MagicMock(side_effect=Exception("oops"))
        results = repo.search_by_semantic("anything", page=1)
        assert results == []

    def test_empty_hits_returns_empty_list(self, repo, fake_client):
        fake_client.collections["tags"].documents.set_search_result([])
        assert repo.search_by_semantic("nothing", page=1) == []


# ---------------------------------------------------------------------------
# search_with_embedding — cached hit path
# ---------------------------------------------------------------------------

class TestSearchWithEmbeddingCachedHit:
    def _repo_with_hit(self, fake_client, matched_name="jazz", expansion="jazz swing bebop"):
        """Repo whose first text-search returns a single hit."""
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        # First search (text lookup) → one hit
        text_hit = {"document": {"id": "1", "name": matched_name, "embedding_name": expansion}}
        # Second search (vector) → results
        vector_hit = {"document": {"id": "1", "name": matched_name}, "vector_distance": 0.12}

        call_count = {"n": 0}
        original_search = fake_client.collections["tags"].documents.search

        def side_effect(params):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"hits": [text_hit]}
            return {"hits": [vector_hit]}

        fake_client.collections["tags"].documents.search = side_effect
        return repo

    def test_returns_tag_from_vector_search(self, fake_client):
        repo = self._repo_with_hit(fake_client)
        results = repo.search_with_embedding("jazz")
        assert len(results) == 1
        assert results[0].name == "jazz"

    def test_fast_expander_not_called_when_cache_hit(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        text_hit = {"document": {"id": "1", "name": "jazz", "embedding_name": "jazz swing"}}
        vector_hit = {"document": {"id": "1", "name": "jazz"}, "vector_distance": 0.1}
        call_count = {"n": 0}

        def side_effect(params):
            call_count["n"] += 1
            return {"hits": [text_hit]} if call_count["n"] == 1 else {"hits": [vector_hit]}

        fake_client.collections["tags"].documents.search = side_effect

        with patch.object(repo.expander, "expand_tag_fast") as mock_fast:
            repo.search_with_embedding("jazz")
        mock_fast.assert_not_called()


# ---------------------------------------------------------------------------
# search_with_embedding — no cache hit → live LLM expansion
# ---------------------------------------------------------------------------

class TestSearchWithEmbeddingLiveExpansion:
    def test_fast_expander_called_when_no_cache_hit(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        # All text searches return empty; vector search returns one hit
        call_count = {"n": 0}

        def side_effect(params):
            call_count["n"] += 1
            if params.get("query_by") == "name":
                return {"hits": []}   # no cache hit
            return {"hits": [{"document": {"id": "9", "name": "kinder"}, "vector_distance": 0.2}]}

        fake_client.collections["tags"].documents.search = side_effect

        with patch.object(repo.expander, "expand_tag_fast", return_value="kinder kids family") as mock_fast:
            results = repo.search_with_embedding("kinder")

        mock_fast.assert_called_once_with("kinder")
        assert len(results) == 1

    def test_returns_empty_list_when_vector_search_raises(self, fake_client):
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        def side_effect(params):
            if params.get("query_by") == "name":
                return {"hits": []}
            raise Exception("typesense down")

        fake_client.collections["tags"].documents.search = side_effect

        with patch.object(repo.expander, "expand_tag_fast", return_value="x"):
            results = repo.search_with_embedding("anything")

        assert results == []


# ---------------------------------------------------------------------------
# search_with_embedding — stem fallback
# ---------------------------------------------------------------------------

class TestSearchWithEmbeddingStemFallback:
    def test_stem_retry_used_when_first_lookup_fails(self, fake_client):
        """If the exact query misses but the stem hits, its expansion is used."""
        with patch("app.repositories.external.search_engine.typesense_tag_search_repo.ExpansionWorker"):
            repo = TypesenseTagSearchRepo(fake_client)

        stem_hit = {"document": {"id": "2", "name": "jam", "embedding_name": "jam jamming improvisation"}}
        vector_hit = {"document": {"id": "2", "name": "jam"}, "vector_distance": 0.15}

        name_call = {"n": 0}

        def side_effect(params):
            if params.get("query_by") == "name":
                name_call["n"] += 1
                # First name call (exact) fails; second (stem) succeeds
                return {"hits": []} if name_call["n"] == 1 else {"hits": [stem_hit]}
            return {"hits": [vector_hit]}

        fake_client.collections["tags"].documents.search = side_effect

        results = repo.search_with_embedding("jamming")
        assert len(results) == 1
        assert results[0].name == "jam"