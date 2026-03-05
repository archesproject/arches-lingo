from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from arches.app.utils.decorators import group_required
from arches.app.utils.response import JSONErrorResponse, JSONResponse

from arches_lingo.utils.dashboard import (
    get_missing_translation_ids,
    paginate_missing_translations,
    parse_scheme_ids,
)


@method_decorator(
    group_required("RDM Administrator", raise_exception=True), name="dispatch"
)
class MissingTranslationsView(View):
    def get(self, request):
        language_code = request.GET.get("language")
        if not language_code:
            return JSONErrorResponse(
                title=_("Missing parameter"),
                message=_("language parameter is required"),
                status=400,
            )

        scheme_ids, error = parse_scheme_ids(request)
        if error:
            return error

        page_number = int(request.GET.get("page", 1))
        items_per_page = int(request.GET.get("items", 25))

        missing_ids = get_missing_translation_ids(language_code, scheme_ids)

        return JSONResponse(
            paginate_missing_translations(missing_ids, page_number, items_per_page)
        )
