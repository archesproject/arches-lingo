from django.db.models.expressions import Func


class JsonbArrayElements(Func):
    """https://forum.djangoproject.com/t/django-4-2-behavior-change-when-using-arrayagg-on-unnested-arrayfield-postgresql-specific/21547/5"""

    arity = 1
    set_returning = True
    function = "JSONB_ARRAY_ELEMENTS"


class LevenshteinLessEqual(Func):
    arity = 3
    function = "LEVENSHTEIN_LESS_EQUAL"
