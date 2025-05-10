import random
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ArchesRouter:
    write_database_alias = None

    for alias, database in settings.DATABASES.items():
        if database.get("WRITE_MODE") is True:
            write_database_alias = alias
            break

    read_database_aliases = [
        alias
        for alias, _database in settings.DATABASES.items()
        if _database.get("READ_MODE") is True
    ]

    def db_for_read(self, model, **hints):
        selected_read_databse = random.choice(self.read_database_aliases)
        logger.info(
            f"[DB ROUTER] Read for {model._meta.label} → {selected_read_databse}"
        )
        return selected_read_databse

    def db_for_write(self, model, **hints):
        logger.info(
            f"[DB ROUTER] Write for {model._meta.label} → {self.write_database_alias}"
        )
        return self.write_database_alias

    def allow_relation(self, obj1, obj2, **hints):
        databases = {obj1._state.db, obj2._state.db}

        if databases <= set(self.read_database_aliases + [self.write_database_alias]):
            return True

        return None

    def allow_migrate(self, database, app_label, **hints):
        return database == self.write_database_alias
