from app.domain_models.user import User

# Just an example to show the modularity of the protocols. Can probably be removed later
# It basically just stores the users in memory. Not in a database.
# If you actually want it to work, set the workers of gunicorn to 1
# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
# The 4 -> 1
class MemUserRepo:
    users = {}
    def get_user(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    def get_user_by_name(self, name: str) -> User | None:
        return next((user for user in self.users.values() if user.name == name), None)

    def create_user(self, name: str, password: str) -> bool:
        self.users[len(self.users) + 1] = User(id=len(self.users) + 1, name=name, hashed_password=password)
        return True
