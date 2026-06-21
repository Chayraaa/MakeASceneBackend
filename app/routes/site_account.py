from flask import Blueprint, request, current_app, json
from app import validate, login_required
from app.domain_models.user import Role, User

site_account = Blueprint('site_account', __name__)


@site_account.route("", methods=["GET"])
@validate
def query_site_accounts():
    pass


@site_account.route("", methods=["POST"])
@login_required(role=Role.MODERATOR)
@validate
def create_site_account(user: User):
    name: str = request.get_json().get("name")
    creator_id: int = request.get_json().get("creator_id")
    creator = current_app.user_service.get_user(creator_id)
    if not creator:
        return {"message": "User not found."}, 404

    if current_app.site_account_service.create_site_account(name, creator):
        return {"message": "Site account created."}, 200
    return {"message": "Failed to create site account."}, 500


@site_account.route("/<int:id>", methods=["GET"])
@validate
def get_site_account(id: int):
    account = current_app.site_account_service.get_site_account_by_id(id)
    if account:
        return {
            "id": account.id,
            "creator_id": account.creator_id,
            "name": account.name,
            "layout": json.loads(account.layout)
        }


@site_account.route("/<int:id>", methods=["PATCH"])
@login_required(role=Role.USER)
@validate
def update_site_account(user: User, id: int):
    account = current_app.site_account_service.get_site_account_by_id(id)
    if not (
            current_app.site_account_service.has_authority(user, account)
            or user.role >= Role.MODERATOR.value
    ):
        return {"message": "You do not have permission to edit this site account."}, 401
    name = request.get_json().get("name") or None
    layout = request.get_json().get("layout") or None
    if current_app.site_account_service.modify_site_account(account, name, layout):
        return {"message": "Site account updated."}, 200
    return {"message": "Failed to update site account."}, 500


@site_account.route("/<int:id>", methods=["DELETE"])
@login_required(role=Role.USER)
@validate
def delete_site_account(user: User):
    pass


@site_account.route("/apply", methods=["POST"])
@login_required(role=Role.USER)
@validate
def apply_to_site_account(user: User):
    pass
