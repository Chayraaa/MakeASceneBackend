from pathlib import Path
import runpy

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_subscription_visibility_timezone_migration_round_trip():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table in ("users", "events", "site_accounts"):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} (id) VALUES (1)"))
        operations = Operations(MigrationContext.configure(connection))
        modules = []
        for name in ("b1f84c92d7a0_add_subscriptions.py", "c28f90a61d32_event_visibility.py", "d84eab6109f2_user_timezone.py"):
            module = runpy.run_path(str(Path("migrations/versions") / name))
            module["upgrade"].__globals__["op"] = operations
            module["upgrade"]()
            modules.append(module)
        assert connection.execute(text("SELECT visible FROM events")).scalar() == 1
        assert connection.execute(text("SELECT timezone FROM users")).scalar() == "UTC"
        for kind in ("event", "site_account"):
            table = f"{kind}_subscriptions"
            connection.execute(text(f"INSERT INTO {table} (user_id, {kind}_id) VALUES (1, 1)"))
            assert connection.execute(text(f"SELECT notifications_enabled FROM {table}")).scalar() == 0
            assert inspect(connection).get_unique_constraints(table)
            assert len(inspect(connection).get_foreign_keys(table)) == 2
        for module in reversed(modules):
            module["downgrade"]()
        inspector = inspect(connection)
        assert "event_subscriptions" not in inspector.get_table_names()
        assert "site_account_subscriptions" not in inspector.get_table_names()
        assert [column["name"] for column in inspector.get_columns("users")] == ["id"]
        assert [column["name"] for column in inspector.get_columns("events")] == ["id"]
    engine.dispose()
