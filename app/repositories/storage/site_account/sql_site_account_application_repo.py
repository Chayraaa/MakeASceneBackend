from app.database_models.site_account.site_account_application_contact_model import SiteAccountApplicationContactModel
from app.database_models.site_account.site_account_application_model import SiteAccountApplicationModel
from app.database_models.site_account.site_account_application_sources_model import SiteAccountApplicationSourcesModel
from app.domain_models.site_account.SiteAccountApplication import SiteAccountApplication
from app.domain_models.user import User


class SqlSiteAccountApplicationRepo:
    def __init__(self, session):
        self.session = session

    def create_application(self, requestor: User, artist_name: str, account_name: str, reason: str, sources: list[str],
                           contacts: list[str]) -> bool:
        application_model = SiteAccountApplicationModel(requestor_id=requestor.id, artist_name=artist_name,
                                                        reason=reason, account_name=account_name)
        self.session.add(application_model)
        self.session.commit()
        application_model = self.session.get(SiteAccountApplicationModel, application_model.id)
        for source in sources:
            source_model = SiteAccountApplicationSourcesModel(application_id=application_model.id, source=source)
            self.session.add(source_model)
        for contact in contacts:
            contact_model = SiteAccountApplicationContactModel(application_id=application_model.id, contact=contact)
            self.session.add(contact_model)
        self.session.commit()
        return True

    def get_application_by_id(self, application_id: int) -> SiteAccountApplication | None:
        model = self.session.get(SiteAccountApplicationModel, application_id)
        if not model:
            return None
        return SiteAccountApplication(id=model.id, requestor_id=model.requestor_id, artist_name=model.artist_name,
                                      account_name=model.account_name,
                                      reason=model.reason, sources=[source.source for source in model.sources],
                                      contacts=[contact.contact for contact in model.contacts])

    def get_applications(self, page: int, page_size: int) -> list[SiteAccountApplication]:
        models = self.session.query(SiteAccountApplicationModel).all()
        models = models[(page - 1) * page_size: page * page_size]
        return [SiteAccountApplication(id=model.id, requestor_id=model.requestor_id, artist_name=model.artist_name, account_name=model.account_name,
                                       reason=model.reason, sources=[source.source for source in model.sources],
                                       contacts=[contact.contact for contact in model.contacts]) for model in models]

    def update_application(self, application: SiteAccountApplication) -> bool:
        model = self.session.get(SiteAccountApplicationModel, application.id)
        if not model:
            return False
        model.requestor_id = application.requestor_id
        model.artist_name = application.artist_name
        model.account_name = application.account_name
        model.reason = application.reason
        for source in model.sources:
            self.session.delete(source)
        for contact in model.contacts:
            self.session.delete(contact)
        for source in application.sources:
            source_model = SiteAccountApplicationSourcesModel(application_id=model.id, source=source)
            self.session.add(source_model)
        for contact in application.contacts:
            contact_model = SiteAccountApplicationContactModel(application_id=model.id, contact=contact)
            self.session.add(contact_model)
        self.session.commit()
        return True

    def delete_application(self, application: SiteAccountApplication) -> bool:
        self.session.delete(self.session.get(SiteAccountApplicationModel, application.id))
        self.session.commit()
        return True
