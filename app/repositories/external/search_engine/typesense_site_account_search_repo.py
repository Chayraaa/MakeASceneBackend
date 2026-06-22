from dataclasses import dataclass

from app.domain_models.site_account.SiteAccount import SiteAccount
import threading

_lock = threading.Lock()
_initialized = False

@dataclass
class SiteAccountSearchResult:
    id: int
    name: str


class TypesenseSiteAccountSearchRepo:

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
            self.client.collections["site_accounts"].retrieve()
            return
        except:
            pass

        self.client.collections.create({
            "name": "site_accounts",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "name", "type": "string"},
            ]
        })

    def add_site_account(self, site_account: SiteAccount) -> bool:
        self._ensure_ready()

        self.client.collections["site_accounts"].documents.upsert({
            "id": str(site_account.id),
            "name": site_account.name,
        })

        return True

    def update_site_account(self, site_account: SiteAccount) -> bool:
        self._ensure_ready()
        self.client.collections["site_accounts"].documents.upsert({
            "id": str(site_account.id),
            "name": site_account.name,
        })

        return True


    def remove_site_account(self, site_account: SiteAccount) -> bool:
        self._ensure_ready()

        try:
            self.client.collections["site_accounts"].documents[site_account.id].delete()
            return True
        except Exception as e:
            print("remove_site_account failed:", e)
            return False

    def search_by_semantic(self, query: str, page: int) -> list[SiteAccountSearchResult]:
        self._ensure_ready()

        try:
            result = self.client.collections["site_accounts"].documents.search({
                "q": query,
                "query_by": "name",
                "num_typos": 2,
                "prefix": "true",
                "per_page": 25,
                "sort_by": "_text_match:desc",
                "page": page
            })

            site_accounts = []
            for hit in result.get("hits", []):
                name = hit["document"]["name"]
                site_accounts.append(SiteAccountSearchResult(
                    id=int(hit["document"]["id"]),
                    name=name
                ))
            return site_accounts
        except Exception as e:
            print("[Site account search] search failed:", e)
            return []
