
from app.database_models.password_reset_token_model import PasswordResetTokenModel
from app.domain_models.password_reset_token import PasswordResetToken
from app.domain_models.user import User


class SqlPasswordResetTokenRepo:
    def __init__(self, session):
        self.session = session

    def create(self, hashed_token: str, user: User) -> bool:
        if self.get_by_token_hash(hashed_token):
            return False
        db_object = PasswordResetTokenModel(user_id=user.id, token_hash=hashed_token)
        self.session.add(db_object)
        self.session.commit()
        return True

    def get_by_token_hash(self, hashed_token: str) -> PasswordResetToken | None:
        db_object = self.session.query(PasswordResetTokenModel).filter_by(token_hash=hashed_token).first()
        if not db_object:
            return None
        return PasswordResetToken(
            id=db_object.id,
            user_id=db_object.user_id,
            hashed_token=db_object.token_hash,
            created_at=db_object.created_at,
            expires_at=db_object.expires_at,
            revoked=db_object.revoked
        )

    def get_by_user(self, user: User) -> list[PasswordResetToken]:
        db_list = self.session.query(PasswordResetTokenModel).filter_by(user_id=user.id).all()
        return [PasswordResetToken(id=db_object.id, user_id=db_object.user_id, hashed_token=db_object.token_hash,
                             created_at=db_object.created_at, expires_at=db_object.expires_at,
                             revoked=db_object.revoked) for db_object in db_list]

    def revoke(self, password_reset_token: PasswordResetToken) -> bool:
        db_object = self.session.get(PasswordResetTokenModel, password_reset_token.id)
        if not db_object:
            return False
        db_object.revoked = True
        self.session.commit()
        return True
