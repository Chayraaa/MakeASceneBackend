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
typesense_client = typesense.Client({
    'nodes': [{
        'host': os.environ.get("TYPESENSE_HOST", "localhost"),
        'port': '8108',
        'protocol': 'http'
    }],
    'api_key': os.environ.get("TYPESENSE_API_KEY", ""),
    'connection_timeout_seconds': 2
})
