from flask import Blueprint, request, current_app, json
from app import validate, login_required
from app.domain_models.user import Role, User

site_account = Blueprint('site_account', __name__)


@site_account.route("", methods=["GET"])
@validate
def query_site_accounts():
    q = request.args.get("q")
    page = request.args.get("page") or 1
    sites = current_app.site_account_service.query_site_accounts(q, page)
    return [site.to_dict() for site in sites], 200, []


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
    if not account:
        return {"message": "Site account not found."}, 404
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
def delete_site_account(user: User, id: int):
    account = current_app.site_account_service.get_site_account_by_id(id)
    if not account:
        return {"message": "Site account not found."}, 404
    if current_app.site_account_service.delete_site_account(account):
        return {"message": "Site account deleted."}, 200
    return {"message": "Failed to delete site account."}, 500


@site_account.route("/application", methods=["POST"])
@login_required(role=Role.USER)
@validate
def apply_to_site_account(user: User):
    artist_name = request.get_json().get("artist_name")
    account_name = request.get_json().get("account_name")
    reason = request.get_json().get("reason")
    sources = request.get_json().get("sources")
    contact = request.get_json().get("contact")
    if current_app.site_account_service.apply_for_site_account(user, artist_name, account_name, reason, sources,
                                                               contact):
        return {"message": "Application submitted."}, 200
    return {"message": "Failed to submit application."}, 500


@site_account.route("/application", methods=["GET"])
@login_required(role=Role.MODERATOR)
@validate
def get_site_account_applications(user: User):
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 25, type=int)
    applications = current_app.site_account_service.get_applications(page, page_size)
    return [application.to_dict() for application in applications], 200, []


@site_account.route("/application/<int:id>", methods=["GET"])
@login_required(role=Role.USER)
@validate
def get_site_account_application(user: User, id: int):
    application = current_app.site_account_service.get_application_by_id(id)
    if not application:
        return {"message": "Application not found."}, 404
    if application.requestor_id == user.id or user.role >= Role.MODERATOR.value:
        return application.to_dict(), 200, []
    return {"message": "You do not have permission to view this application."}, 401, []


@site_account.route("/application/<int:id>", methods=["PATCH"])
@login_required(role=Role.USER)
@validate
def update_site_account_application(user: User, id: int):
    artist_name = request.get_json().get("artist_name") or None
    account_name = request.get_json().get("account_name") or None
    reason = request.get_json().get("reason") or None
    sources = request.get_json().get("sources") or None
    contact = request.get_json().get("contact") or None
    application = current_app.site_account_service.get_application_by_id(id)
    if application.requestor_id == user.id or user.role >= Role.MODERATOR.value:
        if current_app.site_account_service.modify_application(application, artist_name, account_name, reason, sources,
                                                               contact):
            return {"message": "Application updated."}, 200
        return {"message": "Failed to update application."}, 500
    return {"message": "You do not have permission to view this application."}, 401, []


@site_account.route("/application/<int:id>", methods=["DELETE"])
@login_required(role=Role.USER)
@validate
def delete_site_account_application(user: User, id: int):
    application = current_app.site_account_service.get_application_by_id(id)
    if not application:
        return {"message": "Application not found."}, 404
    if application.requestor_id == user.id or user.role >= Role.MODERATOR.value:
        current_app.site_account_service.delete_application(application)
        return {"message": "Application deleted."}, 200
    return {"message": "You do not have permission to view this application."}, 401, []
