from copy import deepcopy

from app.database_models.site_account.site_account_model import SiteAccountModel
from app.domain_models.site_account.SiteAccount import SiteAccount
from app.domain_models.user import User


class SqlSiteAccountRepo:
    def __init__(self, session):
        self.session = session

    def create_site_account(self, name: str, creator: User) -> bool:
        site_account_model = SiteAccountModel(name=name, creator_id=creator.id)
        self.session.add(site_account_model)
        self.session.commit()
        return True

    def get_site_account_by_name(self, name: str) -> SiteAccount | None:
        db_model = self.session.query(SiteAccountModel).filter_by(name=name).first()
        if not db_model:
            return None
        return self._to_domain(db_model)

    def get_site_account_by_id(self, site_account_id: int) -> SiteAccount | None:
        db_model = self.session.get(SiteAccountModel, site_account_id)
        if not db_model:
            return None
        return self._to_domain(db_model)

    @staticmethod
    def _to_domain(model: SiteAccountModel) -> SiteAccount:
        return SiteAccount(
            id=model.id, name=model.name, creator_id=model.creator_id, layout=model.layout,
            profile_picture=model.profile_picture, banner=model.banner, colors=deepcopy(model.colors),
            contact=deepcopy(model.contact), description=model.description, visible=model.visible,
        )

    def update_site_account(self, site_account: SiteAccount) -> bool:
        db_model = self.session.get(SiteAccountModel, site_account.id)
        if not db_model:
            return False
        db_model.name = site_account.name
        db_model.layout = site_account.layout
        db_model.creator_id = site_account.creator_id
        db_model.profile_picture = site_account.profile_picture
        db_model.banner = site_account.banner
        db_model.colors = deepcopy(site_account.colors)
        db_model.contact = deepcopy(site_account.contact)
        db_model.description = site_account.description
        db_model.visible = site_account.visible
        self.session.commit()
        return True

    def remove_site_account(self, site_account: SiteAccount) -> bool:
        db_model = self.session.get(SiteAccountModel, site_account.id)
        if not db_model:
            return False
        self.session.delete(db_model)
        self.session.commit()
        return True
