import os
from queue import Queue

import requests

from app.domain_models.tags.tag import Tag
import threading

_lock = threading.Lock()
_initialized = False


class TypesenseSearchEngineRepo:
    def __init__(self, client):
        self.client = client
        self.worker = LLMWorker(self)
        self.ollama = "http://ollama:11434/api/chat"
        if os.environ.get("FLASK_ENV") == "setup":
            self.ollama = "http://localhost:11434/api/chat"

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
                            "model_name": "ts/multilingual-e5-base"
                        }
                    }
                }
            ]
        })

    def _expand_tag_with_llm(self, tag_name: str) -> str:
        try:
            response = requests.post(
                self.ollama,
                json={
                    "model": "phi3:mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"""
                                You are a tagging system.
                            
                                Expand this tag into semantic search keywords.
                            
                                Rules:
                                - only keywords
                                - no sentences
                                - 5–12 items
                                - focus on meaning, not spelling

                                Tag: {tag_name}
                            """
                        }
                    ],
                    "stream": False
                },
                timeout=60
            )

            return response.json()["message"]["content"]

        except Exception as e:
            print("LLM expansion failed:", e)
            return tag_name

    def _process_llm_tag(self, tag):
        expanded = self._expand_tag_with_llm(tag.name)

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
                "per_page": 25
            })

            return [
                Tag(
                    id=int(hit["document"]["id"]),
                    name=hit["document"]["name"]
                )
                for hit in result.get("hits", [])
            ]
        except Exception as e:
            print("search_for_tag failed:", e)
            return []


class LLMWorker:
    def __init__(self, repo):
        self.repo = repo
        self.queue = Queue()

        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def enqueue(self, tag):
        self.queue.put(tag)

    def _run(self):
        while True:
            tag = self.queue.get()
            try:
                self.repo._process_llm_tag(tag)
            except Exception as e:
                print("worker error:", e)
