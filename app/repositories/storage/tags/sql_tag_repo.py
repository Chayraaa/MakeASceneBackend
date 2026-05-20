from app.database_models.tags.tag_model import TagModel
from app.domain_models.tags.tag import Tag


class SqlTagRepo:
    def __init__(self, session):
        self.session = session

    def create_tag(self, name: str) -> bool:
        if self.get_tag_by_name(name):
            return False
        self.session.add(TagModel(name=name))
        self.session.commit()
        return True

    def get_tag_by_name(self, name: str) -> Tag | None:
        db_tag = self.session.query(TagModel).filter_by(name=name).first()
        if not db_tag:
            return None
        return Tag(id=db_tag.id, name=db_tag.name)

    def get_tag_by_id(self, tag_id: int) -> Tag | None:
        db_tag = self.session.get(TagModel, tag_id)
        if not db_tag:
            return None
        return Tag(id=db_tag.id, name=db_tag.name)

    def update_tag(self, tag: Tag) -> bool:
        db_tag = self.session.get(TagModel, tag.id)
        if not db_tag:
            return False
        db_tag.name = tag.name
        self.session.commit()
        return True

    def remove_tag(self, tag: Tag) -> bool:
        db_tag = self.session.get(TagModel, tag.id)
        if not db_tag:
            return False
        self.session.delete(db_tag)
        self.session.commit()
        return True
