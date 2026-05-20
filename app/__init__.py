import logging
import os
from functools import wraps
from time import sleep

import yaml
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, request, jsonify, current_app
from openapi_core.contrib.flask import FlaskOpenAPIRequest
from openapi_core.exceptions import OpenAPIError
from openapi_core.validation.request.exceptions import InvalidRequestBody
from openapi_core.validation.schemas.exceptions import InvalidSchemaValue

from app.repositories.units_of_work.deploy_unit import DeployUnitOfWork
from app.repositories.units_of_work.test_unit import TestUnitOfWork
from app.services.auth_service import AuthService
from app.services.image_service import ImageService
from app.services.password_service import PasswordService
from app.services.google_oauth_service import GoogleOauthService
from app.services.tag_service import TagService
from app.services.user_service import UserService
from app.extensions import db, migrate
from openapi_core import OpenAPI
import typesense
from app.extensions import typesense_client

# Add all the db database_models here
from app.database_models.user_model import UserModel
from app.database_models.auth.refresh_token_model import RefreshTokenModel
from app.database_models.auth.confirm_token_model import ConfirmTokenModel
from app.database_models.auth.password_reset_token_model import PasswordResetTokenModel
from app.database_models.tags.tag_model import TagModel
from app.database_models.tags.saved_tags_model import SavedTagModel
from app.database_models.tags.blocked_tags_model import BlockedTagModel

# Open API file path
open_api_file_name = "makeascene.openapi.yaml"
api_url = f"/static/{open_api_file_name}"


def setup_logging(app: Flask):
    if app.debug:
        return
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)


def setup_openapi(app: Flask):
    yaml_path = os.path.join(app.root_path, "static", open_api_file_name)
    with open(yaml_path, "r") as f:
        spec = yaml.safe_load(f)

    app.openapi_spec = OpenAPI.from_dict(spec)


def setup_oauth(app: Flask):
    app.config["SECRET_KEY"] = os.getenv("JWT_SECRET")
    oauth = OAuth(app)

    google = oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        }
    )
    app.google = google


def setup_database(app: Flask):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("SQLALCHEMY_DATABASE_URI",
                                                           "postgresql://user:password@localhost:5432/mydb")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.logger.info(f"Connecting to database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    db.init_app(app)
    migrate.init_app(app, db)


########################
# REGULAR EDITING HERE #
########################

def setup_services(app: Flask):
    # Defines the unit of work we are using since some repositories depend on each other.
    # E.g., you can't store the user in a database without the cards in the database.
    # When you, e.g., want to change from a database to a file-based storage, you would need to change the unit of work,
    # not the repositories defined for the services
    # storage_unit_of_work = SqlUnitOfWork()
    storage_unit_of_work = TestUnitOfWork() if app.config["TESTING"] else DeployUnitOfWork()

    app.password_service = PasswordService()
    # This is a user management service that you can give different implementations to
    # A service could also take another service as a dependency. Though make sure to prevent circular dependencies.
    app.user_service = UserService(storage_unit_of_work.user_repo, storage_unit_of_work.email_repo,
                                   storage_unit_of_work.confirm_token_repo)
    app.auth_service = AuthService(storage_unit_of_work.user_repo, storage_unit_of_work.refresh_token_repo,
                                   storage_unit_of_work.confirm_token_repo, storage_unit_of_work.email_repo,
                                   storage_unit_of_work.password_reset_token_repo)
    app.image_service = ImageService(storage_unit_of_work.image_storage,
                                     base_url=os.environ.get("BASE_URL", "http://127.0.0.1:5000"))
    app.google_oauth_service = GoogleOauthService(storage_unit_of_work.user_repo,
                                                  storage_unit_of_work.refresh_token_repo)
    app.tag_service = TagService(storage_unit_of_work.tag_repo, storage_unit_of_work.saved_tag_repo,
                                 storage_unit_of_work.blocked_tag_repo, storage_unit_of_work.search_engine)


# Add all the routes here (see health as example)
def setup_routes(app: Flask):
    from .routes.health import health
    app.register_blueprint(health, url_prefix="/v1/health")
    from .routes.user import users
    app.register_blueprint(users, url_prefix="/v1/users")
    from .routes.image import image
    app.register_blueprint(image, url_prefix="/v1/image")
    from .routes.auth import auth
    app.register_blueprint(auth, url_prefix="/v1/auth")
    from .routes.tag import tags
    app.register_blueprint(tags, url_prefix="/v1/tags")


########################
########################

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        # Get the token from the Authorization header
        token = request.headers.get("Authorization")
        print(request.headers)
        if not token:
            return jsonify({"error": "Token missing"}), 401

        # Check if the token is in the correct format
        parts = token.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Invalid Authorization header"}), 401

        # Parsing and verification of the token
        token = parts[1]
        user_id = PasswordService.verify_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Query the user from the database
        user = current_app.user_service.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401

        # Return the user object to the route handler
        return f(user=user, *args, **kwargs)

    return decorated


# Validation decorator
# AI used for beautifying output when validation failed
def validate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        openapi = current_app.openapi_spec

        try:
            openapi_request = FlaskOpenAPIRequest(request)
            openapi.validate_request(openapi_request)
        except InvalidRequestBody as e:
            if isinstance(e.__cause__, InvalidSchemaValue):
                errors = [err.message for err in e.__cause__.schema_errors]
            else:
                errors = [str(e.__cause__)]
            return jsonify({
                "error": "Request body validation failed",
                "fields": errors
            }), 422
        except OpenAPIError as e:
            return jsonify({
                "error": "Request validation failed",
                "details": str(e)
            }), 422

        return f(*args, **kwargs)

    return decorated


def open_api_page(app):
    from flask_swagger_ui import get_swaggerui_blueprint

    swagger_url = "/docs"

    swagger_ui = get_swaggerui_blueprint(
        swagger_url,
        api_url,
    )

    app.register_blueprint(swagger_ui, url_prefix=swagger_url)


def add_test_tags(app):
    import os
    path = os.path.join(os.path.dirname(__file__), "tags.txt")
    tags = []
    with open(path, "r", encoding="utf-8") as f:
        tags = [line.strip() for line in f if line.strip()]
    with app.app_context():
        for name in tags:
            try:
                app.tag_service.create_tag(name=name)
            except Exception as e:
                print(f"failed to create tag '{name}':", e)
    print("test tags added")


def setup_search_engine(app):
    with app.app_context():
        for _ in range(10):
            try:
                app.tag_service.load_schemas()
                break
            except Exception as e:
                print("failed to load schemas:", e)
                print("retrying...")
                sleep(5)


# Here everything for app creation is inited.
def create_app(testing: bool = False):
    app = Flask(__name__)
    load_dotenv("normal.env")
    load_dotenv("secrets.env")
    if os.getenv("FLASK_ENV") == "migration":
        os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost:5432/makeascene"
    if testing:
        os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True
    if os.getenv("FLASK_ENV") == "setup":
        os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost:5432/makeascene"

    setup_logging(app)
    setup_openapi(app)
    setup_oauth(app)
    setup_database(app)
    setup_services(app)
    setup_routes(app)
    open_api_page(app)

    if os.getenv("FLASK_ENV") == "setup":
        setup_search_engine(app)
        add_test_tags(app)

    return app
