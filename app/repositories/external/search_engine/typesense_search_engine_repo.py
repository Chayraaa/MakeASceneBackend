from app.domain_models.tags.tag import Tag
import threading

_lock = threading.Lock()
_initialized = False


class TypesenseSearchEngineRepo:
    def __init__(self, client):
        self.client = client

    def _ensure_ready(self):
        global _initialized

        if not _initialized:
            with _lock:
                if not _initialized:
                    self._ensure_collection()
                    _initialized = True

    def _ensure_collection(self):
        try:
            self.client.collections["tags"].retrieve()
            return
        except:
            pass

        # Tags:
        self.client.collections.create({
            "name": "tags",
            "fields": [
                {"name": "db_id", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "embedding_name", "type": "string"},
                {
                    "name": "embedding",
                    "type": "float[]",
                    "embed": {
                        "from": [
                            "embedding_name"
                        ],
                        "model_config": {
                            "model_name": "ts/multilingual-e5-base"
                        }
                    }
                }
            ]
        })

    def add_tag(self, tag: Tag) -> bool:
        self._ensure_ready()

        try:
            self.client.collections["tags"].documents.upsert({
                "db_id": str(tag.id),
                "name": tag.name,
                "embedding_name": f"{tag.name} concept category related meaning context"
            })
            return True
        except Exception as e:
            print("add_tag failed:", e)
            return False

    def remove_tag(self, tag: Tag) -> bool:
        self._ensure_ready()

        try:
            self.client.collections["tags"].documents[tag.id].delete()
            return True
        except Exception as e:
            print("remove_tag failed:", e)
            return False

    def search(self, query: str) -> list:
        self._ensure_ready()

        try:
            result = self.client.collections["tags"].documents.search({
                "q": query,
                "query_by": "name"
            })

            return result.get("hits", [])
        except Exception as e:
            print("search failed:", e)
            return []

    def search_for_tag(self, tag_name: str) -> list[Tag]:
        self._ensure_ready()

        try:
            result = self.client.collections["tags"].documents.search({
                "q": tag_name,
                "query_by": "embedding",
                "vector_query": "embedding:([], k:100, distance_threshold:0.7)",
                "per_page": 100
            })

            return [
                Tag(
                    id=int(hit["document"]["db_id"]),
                    name=hit["document"]["name"]
                )
                for hit in result.get("hits", [])
            ]
        except Exception as e:
            print("search_for_tag failed:", e)
            return []
