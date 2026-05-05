from app.domain_models.user import User
from app.database_models.user_model import UserModel
from app.extensions import db


# This is how the user_repo_protocol is implemented, note that it doesn't mention the protocol anywhere
# The protocol just defines the methods in a class the service should accept.
# Any class that provides these methods can be used as a user_repo_protocol
class SqlUserRepo:
    def get_user(self, user_id: int) -> User | None:
        db_user = db.session.get(UserModel, user_id)
        if not db_user:
            return None
        return User(id=db_user.id, hashed_password=db_user.password, oauth=db_user.oauth_method, email=db_user.email)

    def get_user_by_email(self, email: str) -> User | None:
        db_user = db.session.query(UserModel).filter_by(email=email).first()
        if not db_user:
            return None
        return User(id=db_user.id, hashed_password=db_user.password, oauth=db_user.oauth_method, email=db_user.email)

    def create_user(self, password: str, email: str, oauth="local") -> bool:
        db_user = UserModel(password=password, oauth_method=oauth, email=email)
        db.session.add(db_user)
        db.session.commit()
        return True

    def update_user(self, user: User) -> bool:
        db_user = db.session.get(UserModel, user.id)
        db_user.password = user.hashed_password
        db_user.oauth_method = user.oauth
        db_user.email = user.email
        db.session.commit()
        return True
