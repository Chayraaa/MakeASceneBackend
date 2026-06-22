from app.domain_models.tags.tag import Tag
from app.domain_models.user import User
from app.repositories.interfaces.external.search_engine_tag_protocol import SearchEngineTagProtocol
from app.repositories.interfaces.storage.tags.blocked_tag_repo_protocol import BlockedTagRepoProtocol
from app.repositories.interfaces.storage.tags.saved_tag_repo_protocol import SavedTagRepoProtocol
from app.repositories.interfaces.storage.tags.tag_repo_protocol import TagRepoProtocol


class TagService:
    def __init__(self, tag_repo: TagRepoProtocol, saved_tag_repo: SavedTagRepoProtocol,
                 blocked_tag_repo: BlockedTagRepoProtocol, search_engine_repo: SearchEngineTagProtocol):
        self.tag_repo = tag_repo
        self.saved_tag_repo = saved_tag_repo
        self.blocked_tag_repo = blocked_tag_repo
        self.search_engine_repo = search_engine_repo

    def load_schemas(self):
        self.search_engine_repo._ensure_ready()

    def create_tag(self, name: str) -> bool:
        if not self.tag_repo.create_tag(name):
            return False
        tag = self.tag_repo.get_tag_by_name(name)
        if not tag:
            return False
        self.search_engine_repo.add_tag(tag)
        return True

    def query_tags(self, query: str) -> list[Tag]:
        tags = self.search_engine_repo.search_with_embedding(query)
        return tags

    def autocomplete(self, query: str, page: int) -> list[Tag]:
        tags = self.search_engine_repo.search_by_semantic(query, page)
        return tags

    def delete_tag(self, tag: Tag) -> bool:
        tag = self.tag_repo.get_tag_by_id(tag.id)
        if not tag:
            return False
        self.search_engine_repo.remove_tag(tag)
        self.tag_repo.remove_tag(tag)
        return True

    def save_tag(self, user: User, tag: Tag) -> bool:
        if self.tag_repo.get_tag_by_id(tag.id) is None:
            return False
        self.saved_tag_repo.create(user, tag)
        return True

    def block_tag(self, user: User, tag: Tag) -> bool:
        if self.tag_repo.get_tag_by_id(tag.id) is None:
            return False
        self.blocked_tag_repo.create(user, tag)
        return True

    def unsave_tag(self, user: User, tag: Tag) -> bool:
        save_tag = self.saved_tag_repo.get_saved_tag_by_user_and_tag(user, tag)
        if not save_tag:
            return False
        self.saved_tag_repo.remove_saved_tag(save_tag)
        return True

    def unblock_tag(self, user: User, tag: Tag) -> bool:
        blocked_tag = self.blocked_tag_repo.get_blocked_tag_by_user_and_tag(user, tag)
        if not blocked_tag:
            return False
        self.blocked_tag_repo.remove_blocked_tag(blocked_tag)
        return True

    def get_saved_tags(self, user: User, page: int, page_size: int) -> list[Tag | None]:
        user_tags = self.saved_tag_repo.get_saved_tags_by_user(user)
        return [self.tag_repo.get_tag_by_id(saved_tag.tag_id) for saved_tag in user_tags][
            (page - 1) * page_size: page * page_size]

    def get_blocked_tags(self, user: User, page: int, page_size: int) -> list[Tag | None]:
        user_tags = self.blocked_tag_repo.get_blocked_tags_by_user(user)
        return [self.tag_repo.get_tag_by_id(saved_tag.tag_id) for saved_tag in user_tags][
            (page - 1) * page_size: page * page_size]

    def get_tag(self, tag_id: int) -> Tag | None:
        tag = self.tag_repo.get_tag_by_id(tag_id)
        if not tag:
            return None
        return tag
