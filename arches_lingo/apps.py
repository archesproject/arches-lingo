from django.apps import AppConfig
from django.core import checks

from arches_lingo.checks import check_reconciliation_rate_limit


class ArchesLingoConfig(AppConfig):
    name = "arches_lingo"
    verbose_name = "Arches Lingo"
    is_arches_application = True

    def ready(self):
        checks.register(check_reconciliation_rate_limit)
