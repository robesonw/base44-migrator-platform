from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import settings
from app.db.session import Base
from app.db import models  # noqa

config = context.config
# Attempt to configure logging from alembic.ini, but don't fail if it's not configured
if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except (KeyError, ValueError):
        # Logging config not present in alembic.ini, that's ok - app logging is configured separately
        pass
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = {"sqlalchemy.url": settings.database_url}
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
