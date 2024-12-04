from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path

from arches_lingo.views.root import LingoRootView
from arches_lingo.views.api.concepts import ConceptTreeView, ValueSearchView
from arches_lingo.views.api.pythonic_models import (
    ConceptDetailView,
    ConceptListCreateView,
    ConceptStatementDetailView,
    ConceptStatementListCreateView,
    SchemeDetailView,
    SchemeListCreateView,
    SchemeNamespaceView,
    SchemeStatementDetailView,
    SchemeStatementListCreateView,
)

urlpatterns = [
    path("", LingoRootView.as_view(), name="root"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme-root"),
    path("login", LingoRootView.as_view(), name="login"),
    path("advanced-search", LingoRootView.as_view(), name="advanced-search"),
    path("schemes", LingoRootView.as_view(), name="schemes"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme"),
    path("concept/<uuid:id>", LingoRootView.as_view(), name="concept"),
    path("api/concept-tree", ConceptTreeView.as_view(), name="api-concepts"),
    path("api/search", ValueSearchView.as_view(), name="api-search"),
    path("api/concepts", ConceptListCreateView.as_view(), name="concepts-list-create"),
    path("api/concept/<uuid:pk>", ConceptDetailView.as_view(), name="concept-detail"),
    path(
        "api/concept/statements",
        ConceptStatementListCreateView.as_view(),
        name="concept-statements-list-create",
    ),
    path(
        "api/concept/statement/<uuid:pk>",
        ConceptStatementDetailView.as_view(),
        name="concept-statement-detail",
    ),
    path("api/schemes", SchemeListCreateView.as_view(), name="schemes-list-create"),
    path("api/scheme/<uuid:pk>", SchemeDetailView.as_view(), name="scheme-detail"),
    path(
        "api/scheme/<uuid:pk>/namespace",
        SchemeNamespaceView.as_view(),
        name="api-uri-components",
    ),
    path(
        "api/scheme/statements",
        SchemeStatementListCreateView.as_view(),
        name="scheme-statements-list-create",
    ),
    path(
        "api/scheme/statement/<uuid:pk>",
        SchemeStatementDetailView.as_view(),
        name="scheme-statement-detail",
    ),
    path("", include("arches_references.urls")),
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
