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
from app.metrics import site_account_metrics


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

    def _replace_images(self, data: Any, site_account: SiteAccount, _counter: list | None = None):
        if isinstance(data, dict):
            return {k: self._replace_images(v, site_account, _counter) for k, v in data.items()}

        if isinstance(data, list):
            return [self._replace_images(v, site_account, _counter) for v in data]

        if isinstance(data, str) and _looks_like_base64_image(data):
            if _counter is not None:
                _counter[0] += 1
            site_account_metrics.site_account_images_uploaded.inc()
            return self.image_service.save_site_account_image(data, site_account)

        return data

    def create_site_account(self, name: str, creator: User) -> bool:
        if not self.site_account_repo.create_site_account(name, creator):
            site_account_metrics.site_account_created.labels(success='false').inc()
            return False
        site_account = self.site_account_repo.get_site_account_by_name(name)
        if not site_account:
            site_account_metrics.site_account_created.labels(success='false').inc()
            return False
        self.search_engine.add_site_account(site_account)
        site_account_metrics.site_account_created.labels(success='true').inc()
        return True

    def get_site_account_by_id(self, site_account_id: int) -> SiteAccount | None:
        return self.site_account_repo.get_site_account_by_id(site_account_id)

    def modify_site_account(self, site_account: SiteAccount, name: str | None = None, layout: list | None = None,
                            profile_picture: str | None = None, *, picture: str | None = None,
                            banner: str | None = None, colors: list[str] | None = None,
                            contact: list[dict[str, str]] | None = None, description: str | None = None,
                            visible: bool | None = None, creator_id: int | None = None):
        if name is not None:
            site_account.name = name
        if picture is not None:
            profile_picture = picture
        if profile_picture is not None:
            site_account.profile_picture = (
                self.image_service.save_site_account_image(profile_picture, site_account) if profile_picture else None
            )
        if layout is not None:
            image_count = [0]
            with site_account_metrics.site_account_image_processing_duration.time():
                layout = self._replace_images(layout, site_account, image_count)
            site_account_metrics.site_account_layout_image_count.observe(image_count[0])
            site_account.layout = json.dumps(layout)
        if banner is not None:
            site_account.banner = self.image_service.save_site_account_image(banner, site_account) if banner else ""
        if colors is not None:
            site_account.colors = colors
        if contact is not None:
            site_account.contact = contact
        if description is not None:
            site_account.description = description
        if visible is not None:
            site_account.visible = visible
        if creator_id is not None:
            site_account.creator_id = creator_id
        if not self.site_account_repo.update_site_account(site_account):
            return False
        self.search_engine.update_site_account(site_account)
        return True

    def delete_site_account(self, site_account: SiteAccount):
        if self.site_account_repo.remove_site_account(site_account):
            result = self.search_engine.remove_site_account(site_account)
            site_account_metrics.site_account_deleted.labels(success='true').inc()
            return result
        else:
            site_account_metrics.site_account_deleted.labels(success='false').inc()
            return False

    def apply_for_site_account(self, user: User, artist_name: str, account_name: str, reason: str, sources: list[str],
                               contact: list[str]) -> bool:
        result = self.application_repo.create_application(user, artist_name, account_name, reason, sources, contact)
        if result:
            site_account_metrics.site_account_application_submitted.inc()
        return result

    def delete_application(self, application: SiteAccountApplication) -> bool:
        result = self.application_repo.delete_application(application)
        if result:
            site_account_metrics.site_account_application_deleted.inc()
        return result

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
        with site_account_metrics.site_account_search_duration.time():
            results = self.search_engine.search_by_semantic(query, page)
            found = []
            for result in results:
                account = self.get_site_account_by_id(result.id)
                if account is not None and account.visible:
                    found.append(account)
        return found

    def has_authority(self, user: User, site_account: SiteAccount):
        rank = user.role.value if isinstance(user.role, Role) else user.role
        return user.id == site_account.creator_id or rank >= Role.MODERATOR.value
