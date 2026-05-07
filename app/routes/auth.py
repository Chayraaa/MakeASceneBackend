from authlib.integrations.base_client import MismatchingStateError
from flask import Blueprint, request, current_app, url_for

from app import validate

auth = Blueprint('auth', __name__)


# Handles the login. It checks password and username, returns a jwt token which is subsequently checked in the
# login_required decorator.
@auth.route("/sessions", methods=["POST"])
@validate
def login():
    data = request.get_json()
    email = (data.get("email") or "").strip().replace(" ", "")
    password = (data.get("password") or "")
    refresh_token = (data.get("refresh_token") or "")

    if refresh_token != "":
        result = current_app.auth_service.refresh_session(refresh_token)
    else:
        result = current_app.auth_service.authenticate_local(email=email, password=password)
    if not result:
        return {
            "error": "unauthorized",
            "message": "Invalid credentials."
        }, 401
    token, refresh_token = result

    return {
        "message": "Login successful. Use token for authentication.",
        "access_token": token,
        "refresh_token": refresh_token
    }, 201


@auth.route("/oauth/redirect", methods=["GET"])
@validate
def redirect_to():
    param = request.args.get("auth")
    if param == "google":
        redirect_uri = url_for("auth.google_callback", _external=True)
        return current_app.google.authorize_redirect(redirect_uri)
    return {"error": "Invalid authentication provider"}, 400


@auth.route("/oauth/google/callback", methods=["GET"])
@validate
def google_callback():
    try:
        token = current_app.google.authorize_access_token()
    except MismatchingStateError:
        return {
            "error": "oauth_state_mismatch",
            "message": "Login session expired or invalid state. Please try again."
        }, 400

    if not token:
        return {"error": "Failed to authorize with Google"}, 400

    user_info = token.get("userinfo")
    if not user_info:
        return {"error": "Failed to fetch user info from Google"}, 400

    res = current_app.google_oauth_service.authenticate_user(user_info)
    if not res:
        return {"error": "Failed to authenticate user"}, 400
    token, refresh_token = res

    return {
        "message": "Login successful. Use token for authentication.",
        "access_token": token,
        "refresh_token": refresh_token
    }, 201
