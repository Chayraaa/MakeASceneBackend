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
        return SiteAccount(id=db_model.id, name=db_model.name, creator_id=db_model.creator_id, layout=db_model.layout)

    def get_site_account_by_id(self, site_account_id: int) -> SiteAccount | None:
        db_model = self.session.get(SiteAccountModel, site_account_id)
        if not db_model:
            return None
        return SiteAccount(id=db_model.id, name=db_model.name, creator_id=db_model.creator_id, layout=db_model.layout)

    def update_site_account(self, site_account: SiteAccount) -> bool:
        db_model = self.session.get(SiteAccountModel, site_account.id)
        if not db_model:
            return False
        db_model.name = site_account.name
        db_model.layout = site_account.layout
        db_model.creator_id = site_account.creator_id
        self.session.commit()
        return True

    def remove_site_account(self, site_account: SiteAccount) -> bool:
        db_model = self.session.get(SiteAccountModel, site_account.id)
        if not db_model:
            return False
        self.session.delete(db_model)
        self.session.commit()
        return True
