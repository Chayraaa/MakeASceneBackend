from app.repositories.interfaces.user_repo_protocol import UserRepoProtocol
from app.repositories.storage.mem_user_repo import MemUserRepo

# Example of a unit of work that uses in-memory storage. Can be deleted later
class MemUnitOfWork:
    def __init__(self):
        self.user_repo: UserRepoProtocol = MemUserRepo()
