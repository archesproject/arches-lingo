import random
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ArchesRouter:
    master = "default"

    replicas = [
        alias for alias in settings.DATABASES.keys() if alias.startswith("replica")
    ]

    def db_for_read(self, model, **hints):
        chosen = random.choice(self.replicas)
        logger.info(f"[DB ROUTER] Read for {model._meta.label} → {chosen}")
        return chosen

    def db_for_write(self, model, **hints):
        logger.info(f"[DB ROUTER] Write for {model._meta.label} → {self.master}")
        return self.master

    def allow_relation(self, obj1, obj2, **hints):
        dbs = {obj1._state.db, obj2._state.db}
        if dbs <= set(self.replicas + [self.master]):
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        return db == self.master
