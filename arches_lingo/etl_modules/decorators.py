import functools
import logging

from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def load_data_async(func):
    @functools.wraps(func)
    def wrapper(self, request, loadid):
        logger.info(_("Delegating load to Django task"))
        func(self, request)
        return {"success": True, "data": _("delegated_to_task")}

    return wrapper
