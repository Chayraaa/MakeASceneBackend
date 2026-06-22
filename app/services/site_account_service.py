from typing import Any

from flask import json

from app.domain_models.site_account.SiteAccount import SiteAccount
from app.domain_models.site_account.SiteAccountApplication import SiteAccountApplication
from app.domain_models.user import User, Role
from app.repositories.interfaces.external.search_engine_site_account_protocol import SearchEngineSiteAccountProtocol
from app.repositories.interfaces.storage.site_account.site_account_application_repo_protocol import \
    SiteAccountApplicationRepoProtocol
from app.repositories.interfaces.storage.site_account.site_account_repo_protocol import SiteAccountRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.image_service import ImageService


def _looks_like_base64_image(s: str) -> bool:
    return s.startswith("data:image") and "base64," in s


class SiteAccountService:
    def __init__(self, site_account_repo: SiteAccountRepoProtocol, user_repo: UserRepoProtocol,
                 image_service: ImageService, search_engine: SearchEngineSiteAccountProtocol,
                 application_repo: SiteAccountApplicationRepoProtocol):
        self.site_account_repo = site_account_repo
        self.user_repo = user_repo
        self.image_service = image_service
        self.search_engine = search_engine
        self.application_repo = application_repo
        pass

    def _replace_images(self, data: Any, site_account: SiteAccount):
        if isinstance(data, dict):
            return {k: self._replace_images(v, site_account) for k, v in data.items()}

        if isinstance(data, list):
            return [self._replace_images(v, site_account) for v in data]

        if isinstance(data, str) and _looks_like_base64_image(data):
            return self.image_service.save_site_account_image(data, site_account)

        return data

    def create_site_account(self, name: str, creator: User) -> bool:
        if not self.site_account_repo.create_site_account(name, creator):
            return False
        site_account = self.site_account_repo.get_site_account_by_name(name)
        if not site_account:
            return False
        self.search_engine.add_site_account(site_account)
        return True

    def get_site_account_by_id(self, site_account_id: int) -> SiteAccount | None:
        return self.site_account_repo.get_site_account_by_id(site_account_id)

    def modify_site_account(self, site_account: SiteAccount, name: str | None = None, layout: list | None = None):
        if name:
            site_account.name = name
        if layout:
            layout = self._replace_images(layout, site_account)
            site_account.layout = json.dumps(layout)
        self.search_engine.update_site_account(site_account)
        return self.site_account_repo.update_site_account(site_account)

    def delete_site_account(self, site_account: SiteAccount):
        return self.site_account_repo.remove_site_account(site_account)

    def apply_for_site_account(self, user: User, artist_name: str, account_name: str, reason: str, sources: list[str],
                               contact: list[str]) -> bool:
        return self.application_repo.create_application(user, artist_name, account_name, reason, sources, contact)

    def delete_application(self, application: SiteAccountApplication) -> bool:
        return self.application_repo.delete_application(application)

    def get_applications(self, page: int = 1, page_size: int = 25) -> list[SiteAccountApplication]:
        return self.application_repo.get_applications(page, page_size)

    def get_application_by_id(self, application_id: int) -> SiteAccountApplication | None:
        return self.application_repo.get_application_by_id(application_id)

    def modify_application(self, application: SiteAccountApplication, artist_name: str, account_name: str, reason: str, sources: list[str], contact: list[str]):
        application.artist_name = artist_name if artist_name else application.artist_name
        application.account_name = account_name if account_name else application.account_name
        application.reason = reason if reason else application.reason
        application.sources = sources if sources is not None else application.sources
        application.contacts = contact if contact is not None else application.contacts
        return self.application_repo.update_application(application)

    def query_site_accounts(self, query: str, page: int = 1):
        results = self.search_engine.search_by_semantic(query, page)
        found = []
        for result in results:
            found.append(self.get_site_account_by_id(result.id))
        return found

    def has_authority(self, user: User, site_account: SiteAccount):
        return user.id == site_account.creator_id or user.role == Role.MODERATOR
