from app.repositories.interfaces.storage.image_repo_protocol import ImageRepoProtocol
from app.repositories.interfaces.storage.image_storage_protocol import ImageStorageProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.repositories.storage.minio_image_storage import MinioImageStorage
from app.repositories.storage.sql_image_repo import SqlImageRepo
from app.repositories.storage.sql_user_repo import SqlUserRepo


# This is a unit of work. It groups repositories that depend on another.
# If you have multiple units of work that have the same use case but with different repositories as implementation,
# they need to have the same variable names.
class SqlUnitOfWork:
    def __init__(self):
        self.user_repo: UserRepoProtocol = SqlUserRepo()
        self.image_repo: ImageRepoProtocol = SqlImageRepo()
        self.image_storage: ImageStorageProtocol = MinioImageStorage("images")
