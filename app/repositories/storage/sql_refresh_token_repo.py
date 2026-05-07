from flask_sqlalchemy.session import Session

from app.database_models.refresh_token_model import RefreshTokenModel
from app.domain_models.refresh_token import RefreshToken
from app.domain_models.user import User


class SqlRefreshTokenRepo:
    def __init__(self, session):
        self.session = session

    def create(self, hashed_token: str, user: User) -> bool:
        if self.get_by_token_hash(hashed_token):
            return False
        db_object = RefreshTokenModel(user_id=user.id, token_hash=hashed_token)
        self.session.add(db_object)
        self.session.commit()
        return True

    def get_by_token_hash(self, hashed_token: str) -> RefreshToken | None:
        db_object = self.session.query(RefreshTokenModel).filter_by(token_hash=hashed_token).first()
        if not db_object:
            return None
        return RefreshToken(
            id=db_object.id,
            user_id=db_object.user_id,
            hashed_token=db_object.token_hash,
            created_at=db_object.created_at,
            expires_at=db_object.expires_at,
            revoked=db_object.revoked
        )

    def revoke(self, refresh_token: RefreshToken) -> bool:
        db_object = self.session.get(RefreshTokenModel, refresh_token.id)
        if not db_object:
            return False
        db_object.revoked = True
        self.session.commit()
        return True
