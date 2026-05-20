from app.database_models.tags.saved_tags_model import SavedTagModel
from app.domain_models.tags.saved_tag import SavedTag
from app.domain_models.tags.tag import Tag
from app.domain_models.user import User


class SqlSavedTagRepo:
    def __init__(self, session):
        self.session = session

    def create(self, user: User, tag: Tag) -> bool:
        db_saved_tag = SavedTagModel(user_id=user.id, tag_id=tag.id)
        self.session.add(db_saved_tag)
        self.session.commit()
        return True

    def get_saved_tags_by_user(self, user: User) -> list[SavedTag]:
        db_list = self.session.query(SavedTagModel).filter_by(user_id=user.id).all()
        return [SavedTag(id=db_object.id, user_id=db_object.user_id, tag_id=db_object.tag_id) for db_object in db_list]

    def get_saved_tags_by_tag(self, tag: Tag) -> list[SavedTag]:
        db_list = self.session.query(SavedTagModel).filter_by(tag_id=tag.id).all()
        return [SavedTag(id=db_object.id, user_id=db_object.user_id, tag_id=db_object.tag_id) for db_object in db_list]

    def get_saved_tag_by_id(self, saved_tag_id: int) -> SavedTag | None:
        db_saved_tag = self.session.get(SavedTagModel, saved_tag_id)
        if not db_saved_tag:
            return None
        return SavedTag(id=db_saved_tag.id, user_id=db_saved_tag.user_id, tag_id=db_saved_tag.tag_id)

    def get_saved_tag_by_user_and_tag(self, user: User, tag: Tag) -> SavedTag | None:
        db_saved_tag = self.session.query(SavedTagModel).filter_by(user_id=user.id, tag_id=tag.id).first()
        if not db_saved_tag:
            return None
        return SavedTag(id=db_saved_tag.id, user_id=db_saved_tag.user_id, tag_id=db_saved_tag.tag_id)

    def remove_saved_tag(self, saved_tag: SavedTag) -> bool:
        db_saved_tag = self.session.get(SavedTagModel, saved_tag.id)
        if not db_saved_tag:
            return False
        self.session.delete(db_saved_tag)
        self.session.commit()
        return True

    def update_saved_tag(self, saved_tag: SavedTag) -> bool:
        db_saved_tag = self.session.get(SavedTagModel, saved_tag.id)
        if not db_saved_tag:
            return False
        db_saved_tag.user_id = saved_tag.user_id
        db_saved_tag.tag_id = saved_tag.tag_id
        self.session.commit()
        return True
