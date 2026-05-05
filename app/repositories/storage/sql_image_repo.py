from app.database_models.user_model import UserModel

from app.extensions import db


class SqlImageRepo:

    def save_user_image(self, key: str, user_id) -> str:
        user = db.session.get(UserModel, user_id)
        user.profile_picture_key = key
        db.session.commit()
        return key

    def get_card_keys_by_user_id(self, user_id: int) -> list[str]:
        return [card.image_key for card in db.session.get(UserModel, user_id).cards]

    def get_user_key_by_id(self, user_id: int) -> str:
        return db.session.get(UserModel, user_id).profile_picture_key

    def has_profile_picture(self, user_id: int) -> bool:
        user = db.session.get(UserModel, user_id)

        if user is None:
            return False
        return db.session.get(UserModel, user_id).profile_picture_key != ""
