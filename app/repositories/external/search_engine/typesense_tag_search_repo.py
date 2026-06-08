from nltk.stem.snowball import SnowballStemmer

from app.domain_models.tags.tag import Tag
import threading

from app.helper.llm.expansion_worker import ExpansionWorker
from app.helper.llm.tag_expander import TagExpander

_lock = threading.Lock()
_initialized = False
_stemmer_en = SnowballStemmer("english")
_stemmer_de = SnowballStemmer("german")


class TypesenseTagSearchRepo:

    def __init__(self, client):
        self.client = client
        self.expander = TagExpander()
        self.worker = ExpansionWorker(self._process_tag)

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
                {"name": "id", "type": "string"},
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
                            "model_name": "ts/paraphrase-multilingual-mpnet-base-v2"
                        }
                    }
                }
            ]
        })

    def _process_tag(self, tag):
        expanded = self.expander.expand_tag_slow(tag.name)

        self.client.collections["tags"].documents.upsert({
            "id": str(tag.id),
            "name": tag.name,
            "embedding_name": f"{tag.name} {expanded}"
        })

    def add_tag(self, tag: Tag) -> bool:
        self._ensure_ready()

        self.client.collections["tags"].documents.upsert({
            "id": str(tag.id),
            "name": tag.name,
            "embedding_name": tag.name
        })

        self.worker.enqueue(tag)

        return True

    def remove_tag(self, tag: Tag) -> bool:
        self._ensure_ready()

        try:
            self.client.collections["tags"].documents[tag.id].delete()
            return True
        except Exception as e:
            print("remove_tag failed:", e)
            return False

    def search_by_semantic(self, query: str, page: int) -> list[Tag]:
        self._ensure_ready()

        try:
            result = self.client.collections["tags"].documents.search({
                "q": query,
                "query_by": "name",
                "num_typos": 2,
                "prefix": "true",
                "per_page": 25,
                "page": page
            })

            tags = []
            for hit in result.get("hits", []):
                name = hit["document"]["name"]
                tags.append(Tag(
                    id=int(hit["document"]["id"]),
                    name=name
                ))
            return tags
        except Exception as e:
            print("[Tag search] search failed:", e)
            return []

    def _stem(self, query: str) -> str:
        en = _stemmer_en.stem(query)
        de = _stemmer_de.stem(query)
        # Pick whichever stem is shorter — more likely to match partial tag names
        return min(en, de, key=len)

    def search_for_tag(self, tag_name: str) -> list[Tag]:
        self._ensure_ready()

        search_query = tag_name
        print(f"[Tag Search] Searching for '{tag_name}'")
        stemmed = self._stem(tag_name)

        try:
            # Original query with typo tolerance and prefix
            exact = self.client.collections["tags"].documents.search({
                "q": tag_name,
                "query_by": "name",
                "num_typos": 1,
                "prefix": "true",
                "per_page": 1
            })
            hits = exact.get("hits", [])

            # If no hit, retry with the stem (e.g. "Jamming" → "jam")
            if not hits and stemmed != tag_name.lower():
                print(f"[Tag Search] No hit for '{tag_name}', retrying with stem '{stemmed}'")
                stemmed_result = self.client.collections["tags"].documents.search({
                    "q": stemmed,
                    "query_by": "name",
                    "num_typos": 0,
                    "prefix": "true",
                    "per_page": 1
                })
                hits = stemmed_result.get("hits", [])

            if hits:
                matched_name = hits[0]["document"]["name"]
                search_query = hits[0]["document"]["embedding_name"]
                print(f"[Tag Search] Matched '{matched_name}' → using its expansion")
            else:
                # If no hit with stem, expand via llm (less than 1s waiting time tolerance)
                print(f"[Tag Search] No cached match, expanding query live")
                search_query = self.expander.expand_tag_fast(tag_name)
                print(f"[Tag Search] Expansion: {search_query}")

        except Exception as e:
            print(f"[Tag Search] Lookup failed: {e}")

        try:
            result = self.client.collections["tags"].documents.search({
                "q": search_query,
                "query_by": "embedding",
                "vector_query": "embedding:([], k:100, distance_threshold:0.35)",
                "per_page": 25
            })

            tags = []
            for hit in result.get("hits", []):
                distance = hit.get("vector_distance", None)
                name = hit["document"]["name"]
                print(f"  {distance:.4f}  {name}")
                tags.append(Tag(
                    id=int(hit["document"]["id"]),
                    name=name
                ))

            return tags

        except Exception as e:
            print("search_for_tag failed:", e)
            return []
