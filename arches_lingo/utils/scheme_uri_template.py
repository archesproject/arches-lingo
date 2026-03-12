from django.conf import settings


def default_scheme_uri_template_value():
    return (
        f"{settings.PUBLIC_SERVER_ADDRESS.rstrip('/')}"
        "/schemes/<scheme_identifier>/concepts/<concept_identifier>"
    )
