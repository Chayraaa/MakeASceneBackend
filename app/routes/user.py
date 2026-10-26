from authlib.integrations.base_client import MismatchingStateError
from flask import Blueprint, request, current_app, url_for

from app import validate, login_required
from app.domain_models.tags.tag import Tag
from app.domain_models.user import User

# This route handles user creation, modification, deletion, login, and logout
users = Blueprint("users", __name__)


# Creates a user and adds it to the database
@users.route("", methods=["POST"])
@validate
def create_user():
    data = request.get_json()
    email = (data.get("email") or "").strip().replace(" ", "")
    password = data.get("password")

    if current_app.user_service.create_user(email, password):
        return {"message": "User created successfully."}, 201
    else:
        return {"message": "User already exists."}, 409


@users.route("/me", methods=["GET"])
@validate
@login_required()
def info(user: User):
    return {
        "id": user.id,
        "email": user.email,
        "mature": user.mature,
        "email_preference": user.email_preference,
    }, 200


@users.route("/me", methods=["PATCH"])
@validate
@login_required()
def update(user: User):
    data = request.get_json()

    mature = data.get("mature")
    email_preference = data.get("email_preference")

    user.mature = mature if mature is not None else user.mature
    user.email_preference = (
        email_preference if email_preference is not None else user.email_preference
    )
    current_app.user_service.update_user(user)
    return {
        "id": user.id,
        "email": user.email,
        "mature": user.mature,
        "email_preference": user.email_preference,
    }, 200


@users.route("/me", methods=["DELETE"])
@validate
@login_required()
def delete(user: User):
    if current_app.user_service.delete_user(user):
        return {"message": "Deletion was successful"}, 200
    return {"message": "Deletion failed"}, 500


@users.route("/me/messages", methods=["GET"])
@login_required()
@validate
def get_messages(user: User):
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 25, type=int)
    if page < 1 or page_size < 1:
        return {"error": "page and page_size must be positive."}, 422

    messages = current_app.message_service.get_messages(user, page, page_size)
    if messages is None:
        return {"error": "Failed to retrieve messages."}, 500
    return {"messages": [message.to_dict() for message in messages]}, 200


@users.route("/me/messages/<int:id>", methods=["PATCH"])
@login_required()
@validate
def update_message(user: User, id: int):
    data = request.get_json()
    result = current_app.message_service.mark_message_as_read(id, user, data["read"])
    if result is None:
        return {"error": "Message not found."}, 404
    if not result:
        return {"error": "Message could not be updated."}, 500
    return {}, 200


@users.route("/me/messages/<int:id>", methods=["DELETE"])
@login_required()
@validate
def delete_message(user: User, id: int):
    result = current_app.message_service.delete_message(id, user)
    if result is None:
        return {"error": "Message not found."}, 404
    if not result:
        return {"error": "Message could not be deleted."}, 500
    return {}, 200


@users.route("/me/tags", methods=["GET"])
@validate
@login_required()
def get_saved_tags(user: User):
    page = request.args.get("page", 1, type=int)
    size = request.args.get("page_size", 25, type=int)
    res = current_app.tag_service.get_saved_tags(user, page, size)
    return {"tags": [{
        "id": tag.id,
        "name": tag.name,
        "parent": tag.parent,
    } for tag in res]}, 200


@users.route("/me/tags/<int:id>", methods=["POST"])
@validate
@login_required()
def subscribe_to_tag(user: User, id: int):
    if current_app.tag_service.save_tag(user, Tag(id=id, name="")):
        return {"message": "Tag saved."}, 200
    return {"message": "Tag was not found."}, 404


@users.route("/me/tags/<int:id>", methods=["DELETE"])
@validate
@login_required()
def unsubscribe_tag(user: User, id: int):
    if current_app.tag_service.unsave_tag(user, Tag(id=id, name="")):
        return {"message": "Tag removed."}, 200
    return {"message": "Tag was not found."}, 404


@users.route("/me/tags/block", methods=["GET"])
@validate
@login_required()
def get_blocked_tags(user: User):
    page = request.args.get("page", 1, type=int)
    size = request.args.get("page_size", 25, type=int)
    res = current_app.tag_service.get_blocked_tags(user, page, size)
    return {"tags": [{
        "id": tag.id,
        "name": tag.name,
        "parent": tag.parent,
    } for tag in res]}, 200


@users.route("/me/tags/block/<int:id>", methods=["POST"])
@validate
@login_required()
def block_tag(user: User, id: int):
    if current_app.tag_service.block_tag(user, Tag(id=id, name="")):
        return {"message": "Tag blocked."}, 200
    return {"message": "Tag was not found."}, 404


@users.route("/me/tags/block/<int:id>", methods=["DELETE"])
@validate
@login_required()
def unblock_tag(user: User, id: int):
    if current_app.tag_service.unblock_tag(user, Tag(id=id, name="")):
        return {"message": "Tag unblocked."}, 200
    return {"message": "Tag was not found."}, 404
