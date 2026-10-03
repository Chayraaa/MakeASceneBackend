import typesense
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os

if os.getenv("FLASK_ENV") == "setup":
    os.environ["TYPESENSE_HOST"] = "localhost"
if os.getenv("FLASK_ENV") == "migration":
    os.environ["TYPESENSE_API_KEY"] = "asdfg"

db = SQLAlchemy()
migrate = Migrate()
_typesense_node = [{
    'host': os.environ.get("TYPESENSE_HOST", "localhost"),
    'port': '8108',
    'protocol': 'http'
}]
_typesense_key = os.environ.get("TYPESENSE_API_KEY", "")

typesense_client = typesense.Client({
    'nodes': _typesense_node,
    'api_key': _typesense_key,
    'connection_timeout_seconds': 2
})

# Used only during collection initialisation, which triggers a model download
# on first run (~440 MB). Normal search requests still use the 2s client.
typesense_init_client = typesense.Client({
    'nodes': _typesense_node,
    'api_key': _typesense_key,
    'connection_timeout_seconds': 300
})
