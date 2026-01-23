from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from arches_lingo.views.root import LingoRootView
from arches_lingo.views.api.concepts import (
    ConceptTreeView,
    ValueSearchView,
    ConceptResourceView,
    ConceptRelationshipView,
)
from arches_lingo.views.api.schemes import SchemeResourceView
from arches_lingo.views.api.generic import (
    LingoResourceDetailView,
    LingoResourceListCreateView,
    LingoTileDetailView,
    LingoTileListCreateView,
)
from arches_lingo.views.api.concept_identifier_counter import (
    ConceptIdentifierCounterView,
)

handler400 = "arches.app.views.main.custom_400"
handler403 = "arches.app.views.main.custom_403"
handler404 = "arches.app.views.main.custom_404"
handler500 = "arches.app.views.main.custom_500"

urlpatterns = [
    path("", LingoRootView.as_view(), name="root"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme-root"),
    path("login", LingoRootView.as_view(), name="login"),
    path("advanced-search", LingoRootView.as_view(), name="advanced-search"),
    path("schemes", LingoRootView.as_view(), name="schemes"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme"),
    path("scheme/new", LingoRootView.as_view(), name="new-scheme"),
    path("concept/<uuid:id>", LingoRootView.as_view(), name="concept"),
    path("concept/new", LingoRootView.as_view(), name="new-concept"),
    path("api/concept-tree", ConceptTreeView.as_view(), name="api-concepts"),
    path("api/search", ValueSearchView.as_view(), name="api-search"),
    path(
        "api/scheme/<uuid:scheme_resource_instance_id>/concept-identifier-counter",
        ConceptIdentifierCounterView.as_view(),
        name="api-concept-identifier-counter",
    ),
    path(
        "api/lingo/scheme-resource",
        SchemeResourceView.as_view(),
        name="api-lingo-scheme-resource",
    ),
    path(
        "api/lingo/concept-resources",
        ConceptResourceView.as_view(),
        name="api-lingo-concept-resources",
    ),
    path(
        "api/lingo/concept-relationships",
        ConceptRelationshipView.as_view(),
        name="api-lingo-concept-relationships",
    ),
    path(
        "api/lingo/<slug:graph>",
        LingoResourceListCreateView.as_view(),
        name="api-lingo-resources",
    ),
    path(
        "api/lingo/<slug:graph>/<uuid:pk>",
        LingoResourceDetailView.as_view(),
        name="api-lingo-resource",
    ),
    path(
        "api/lingo/<slug:graph>/<uuid:pk>/<slug:nodegroup_alias>",
        LingoResourceDetailView.as_view(),
        name="api-lingo-resource-partial",
    ),
    path(
        "api/lingo/<slug:graph>/<slug:nodegroup_alias>",
        LingoTileListCreateView.as_view(),
        name="api-lingo-tiles",
    ),
    path(
        "api/lingo/<slug:graph>/<slug:nodegroup_alias>/<uuid:pk>",
        LingoTileDetailView.as_view(),
        name="api-lingo-tile",
    ),
    path("", include("arches_controlled_lists.urls")),
    path("", include("arches_component_lab.urls")),
]

# Ensure Arches core urls are superseded by project-level urls
urlpatterns.append(path("", include("arches.urls")))

# Adds URL pattern to serve media files during development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Only handle i18n routing in active project. This will still handle the routes provided by Arches core and Arches applications,
# but handling i18n routes in multiple places causes application errors.
if settings.ROOT_URLCONF == __name__:
    if settings.SHOW_LANGUAGE_SWITCH is True:
        urlpatterns = i18n_patterns(*urlpatterns)

    urlpatterns.append(path("i18n/", include("django.conf.urls.i18n")))
