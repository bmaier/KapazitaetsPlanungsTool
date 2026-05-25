"""
Alembic-Migrationsumgebung für BorderCapControl.
Async-fähig mit asyncpg-Treiber.
"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# alembic.ini-Konfiguration lesen
config = context.config

# Logging aus alembic.ini konfigurieren
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DB-URL aus Umgebungsvariable überschreiben (kein Hardcoding!)
database_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://bordercap:bordercap_dev@postgres:5432/bordercap",
)
config.set_main_option("sqlalchemy.url", database_url)

# target_metadata ist None, da wir Schema-DDL direkt in SQL schreiben
# (init.sql + diese Migration), nicht über SQLAlchemy-Models
target_metadata = None


def run_migrations_offline() -> None:
    """
    Offline-Modus: generiert SQL-Skript ohne DB-Verbindung.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Online-Modus: führt Migrationen gegen echte DB aus.
    Nutzt asyncpg via SQLAlchemy AsyncEngine.
    """
    connectable = create_async_engine(database_url, echo=False)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
