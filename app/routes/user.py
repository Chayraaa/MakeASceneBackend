from authlib.integrations.base_client import MismatchingStateError
from flask import Blueprint, request, current_app, url_for

from app import validate, login_required
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