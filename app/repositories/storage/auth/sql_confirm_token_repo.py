from app.database_models.auth.confirm_token_model import ConfirmTokenModel
from app.domain_models.auth.confirm_token import ConfirmToken
from app.domain_models.user import User


class SqlConfirmTokenRepo:
    def __init__(self, session):
        self.session = session

    def create(self, hashed_token: str, user: User) -> bool:
        if self.get_by_token_hash(hashed_token):
            return False
        db_object = ConfirmTokenModel(user_id=user.id, token_hash=hashed_token)
        self.session.add(db_object)
        self.session.commit()
        return True

    def get_by_token_hash(self, hashed_token: str) -> ConfirmToken | None:
        db_object = self.session.query(ConfirmTokenModel).filter_by(token_hash=hashed_token).first()
        if not db_object:
            return None
        return ConfirmToken(
            id=db_object.id,
            user_id=db_object.user_id,
            hashed_token=db_object.token_hash,
            created_at=db_object.created_at,
            expires_at=db_object.expires_at,
            revoked=db_object.revoked
        )

    def revoke(self, confirm_token: ConfirmToken) -> bool:
        db_object = self.session.get(ConfirmTokenModel, confirm_token.id)
        if not db_object:
            return False
        db_object.revoked = True
        self.session.commit()
        return True
