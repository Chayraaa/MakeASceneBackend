import logging
import os
from functools import wraps

import yaml
from authlib.integrations.flask_client import OAuth
from flask import Flask, request, jsonify, current_app
from openapi_core.contrib.flask import FlaskOpenAPIRequest
from openapi_core.exceptions import OpenAPIError
from openapi_core.validation.request.exceptions import InvalidRequestBody
from openapi_core.validation.schemas.exceptions import InvalidSchemaValue
from sqlalchemy import inspect

from app.repositories.units_of_work.deploy_unit import DeployUnitOfWork
from app.repositories.units_of_work.test_unit import TestUnitOfWork
from app.services.auth_service import AuthService
from app.services.image_service import ImageService
from app.services.password_service import PasswordService
from app.services.google_oauth_service import GoogleOauthService
from app.services.user_service import UserService
from app.extensions import db
from openapi_core import OpenAPI

# Add all the db database_models here
from app.database_models.user_model import UserModel
from app.database_models.refresh_token_model import RefreshTokenModel

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

    with app.app_context():
        inspector = inspect(db.engine)
        for table_name, table_obj in db.metadata.tables.items():
            if not inspector.has_table(table_name):
                try:
                    table_obj.create(db.engine)
                    app.logger.info(f"Created table: {table_name}")
                except Exception as e:
                    app.logger.error(f"Error creating table {table_name}")
            else:
                app.logger.info(f"Table {table_name} already exists")


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
                                   storage_unit_of_work.confirm_token_repo)
    app.image_service = ImageService(storage_unit_of_work.image_storage,
                                     base_url=os.environ.get("BASE_URL", "http://127.0.0.1:5000"))
    app.google_oauth_service = GoogleOauthService(storage_unit_of_work.user_repo,
                                                  storage_unit_of_work.refresh_token_repo)


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


# Here everything for app creation is inited.
def create_app(testing: bool = False):
    app = Flask(__name__)
    if testing:
        os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["TESTING"] = True

    setup_logging(app)
    setup_openapi(app)
    setup_oauth(app)
    setup_database(app)
    setup_services(app)
    setup_routes(app)
    open_api_page(app)

    return app
