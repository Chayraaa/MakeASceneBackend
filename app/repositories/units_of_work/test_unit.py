from app.extensions import db
from app.repositories.external.resend_email_repo import ResendEmailRepo
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.external.search_engine_protocol import SearchEngineTagProtocol
from app.repositories.interfaces.storage.auth.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.image_storage_protocol import ImageStorageProtocol
from app.repositories.interfaces.storage.auth.password_reset_token_repo_protocol import PasswordResetTokenRepoProtocol
from app.repositories.interfaces.storage.auth.refresh_token_repo_protocol import RefreshTokenRepoProtocol
from app.repositories.interfaces.storage.tags.blocked_tag_repo_protocol import BlockedTagRepoProtocol
from app.repositories.interfaces.storage.tags.saved_tag_repo_protocol import SavedTagRepoProtocol
from app.repositories.interfaces.storage.tags.tag_repo_protocol import TagRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.repositories.storage.image.mem_image_storage import InMemoryImageStorage
from app.repositories.storage.auth.sql_confirm_token_repo import SqlConfirmTokenRepo
from app.repositories.storage.auth.sql_password_reset_token_repo import SqlPasswordResetTokenRepo
from app.repositories.storage.auth.sql_refresh_token_repo import SqlRefreshTokenRepo
from app.repositories.storage.sql_user_repo import SqlUserRepo
from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo
from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo
from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo


# This is a unit of work. It groups repositories that depend on another.
# If you have multiple units of work that have the same use case but with different repositories as implementation,
# they need to have the same variable names.
class TestUnitOfWork:
    __test__ = False
    def __init__(self):
        self.user_repo: UserRepoProtocol = SqlUserRepo(db.session)
        self.image_storage: ImageStorageProtocol = InMemoryImageStorage("images")
        self.refresh_token_repo: RefreshTokenRepoProtocol = SqlRefreshTokenRepo(db.session)
        self.email_repo: EmailProtocol = ResendEmailRepo()
        self.confirm_token_repo: ConfirmTokenRepoProtocol = SqlConfirmTokenRepo(db.session)
        self.password_reset_token_repo: PasswordResetTokenRepoProtocol = SqlPasswordResetTokenRepo(db.session)
        self.tag_repo: TagRepoProtocol = SqlTagRepo(db.session)
        self.saved_tag_repo: SavedTagRepoProtocol = SqlSavedTagRepo(db.session)
        self.blocked_tag_repo: BlockedTagRepoProtocol = SqlBlockedTagRepo(db.session)
        self.search_engine: SearchEngineTagProtocol = None
