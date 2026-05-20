from app.database_models.tags.blocked_tags_model import BlockedTagModel
from app.domain_models.tags.blocked_tag import BlockedTag
from app.domain_models.tags.tag import Tag
from app.domain_models.user import User


class SqlBlockedTagRepo:
    def __init__(self, session):
        self.session = session

    def create(self, user: User, tag: Tag) -> bool:
        db_blocked_tag = BlockedTagModel(user_id=user.id, tag_id=tag.id)
        self.session.add(db_blocked_tag)
        self.session.commit()
        return True

    def get_blocked_tags_by_user(self, user: User) -> list[BlockedTag]:
        db_list = self.session.query(BlockedTagModel).filter_by(user_id=user.id).all()
        return [BlockedTag(id=db_object.id, user_id=db_object.user_id, tag_id=db_object.tag_id) for db_object in
                db_list]

    def get_blocked_tags_by_tag(self, tag: Tag) -> list[BlockedTag]:
        db_list = self.session.query(BlockedTagModel).filter_by(tag_id=tag.id).all()
        return [BlockedTag(id=db_object.id, user_id=db_object.user_id, tag_id=db_object.tag_id) for db_object in
                db_list]

    def get_blocked_tag_by_id(self, blocked_tag_id: int) -> BlockedTag | None:
        db_blocked_tag = self.session.get(BlockedTagModel, blocked_tag_id)
        if not db_blocked_tag:
            return None
        return BlockedTag(id=db_blocked_tag.id, user_id=db_blocked_tag.user_id, tag_id=db_blocked_tag.tag_id)

    def get_blocked_tag_by_user_and_tag(self, user: User, tag: Tag) -> BlockedTag | None:
        db_blocked_tag = self.session.query(BlockedTagModel).filter_by(user_id=user.id, tag_id=tag.id).first()
        if not db_blocked_tag:
            return None
        return BlockedTag(id=db_blocked_tag.id, user_id=db_blocked_tag.user_id, tag_id=db_blocked_tag.tag_id)

    def remove_blocked_tag(self, blocked_tag: BlockedTag) -> bool:
        db_blocked_tag = self.session.get(BlockedTagModel, blocked_tag.id)
        if not db_blocked_tag:
            return False
        self.session.delete(db_blocked_tag)
        self.session.commit()
        return True

    def update_blocked_tag(self, blocked_tag: BlockedTag) -> bool:
        db_blocked_tag = self.session.get(BlockedTagModel, blocked_tag.id)
        if not db_blocked_tag:
            return False
        db_blocked_tag.user_id = blocked_tag.user_id
        db_blocked_tag.tag_id = blocked_tag.tag_id
        self.session.commit()
        return True
