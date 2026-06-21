from typing import Any

from flask import json

from app.domain_models.site_account.SiteAccount import SiteAccount
from app.domain_models.user import User
from app.repositories.interfaces.storage.site_account.site_account_repo_protocol import SiteAccountRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.image_service import ImageService


def _looks_like_base64_image(s: str) -> bool:
    return s.startswith("data:image") and "base64," in s


class SiteAccountService:
    def __init__(self, site_account_repo: SiteAccountRepoProtocol, user_repo: UserRepoProtocol,
                 image_service: ImageService):
        self.site_account_repo = site_account_repo
        self.user_repo = user_repo
        self.image_service = image_service
        pass

    def _replace_images(self, data: Any, site_account: SiteAccount):
        if isinstance(data, dict):
            return {k: self._replace_images(v, site_account) for k, v in data.items()}

        if isinstance(data, list):
            return [self._replace_images(v, site_account) for v in data]

        if isinstance(data, str) and _looks_like_base64_image(data):
            return self.image_service.save_site_account_image(data,site_account)

        return data

    def create_site_account(self, name: str, creator: User) -> bool:
        return self.site_account_repo.create_site_account(name, creator)

    def get_site_account_by_id(self, site_account_id: int) -> SiteAccount | None:
        return self.site_account_repo.get_site_account_by_id(site_account_id)

    def modify_site_account(self, site_account: SiteAccount, name: str | None = None, layout: list | None = None):
        if name:
            site_account.name = name
        if layout:
            layout = self._replace_images(layout, site_account)
            site_account.layout = json.dumps(layout)
        return self.site_account_repo.update_site_account(site_account)

    def delete_site_account(self, site_account: SiteAccount):
        return self.site_account_repo.remove_site_account(site_account)

    def apply_for_site_account(self, user: User, artist_name: str, account_name: str, reason: str, sources: list[str], contact: list[str]):
        pass

    def query_site_accounts(self, query: str):
        pass

    def has_authority(self, user: User, site_account: SiteAccount):
        return user.id == site_account.creator_id
