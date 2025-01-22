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
    GroupRdmSystemSerializerView,
    PersonRdmSystemSerializerView,
    SchemeCreationView,
    SchemeRightsView,
    SchemeDetailView,
    SchemeLabelTileView,
    SchemeLabelView,
    SchemeLabelCreateView,
    SchemeListCreateView,
    SchemeNamespaceView,
    SchemeNoteTileView,
    SchemeNoteView,
    SchemeNoteCreateView,
    SchemeStatementDetailView,
    SchemeStatementListCreateView,
    TextualWorkRdmSystemSerializerView,
    PersonRdmSystemSerializerView,
    GroupRdmSystemSerializerView,
)

urlpatterns = [
    path("", LingoRootView.as_view(), name="root"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme-root"),
    path("login", LingoRootView.as_view(), name="login"),
    path("advanced-search", LingoRootView.as_view(), name="advanced-search"),
    path("schemes", LingoRootView.as_view(), name="schemes"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme"),
    path("scheme/new", LingoRootView.as_view(), name="new-scheme"),
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
        "api/scheme/<uuid:pk>/creation",
        SchemeCreationView.as_view(),
        name="api-scheme-creation",
    ),
    path(
        "api/scheme/<uuid:pk>/label",
        SchemeLabelView.as_view(),
        name="api-scheme-label",
    ),
    path(
        "api/scheme/<uuid:resource_id>/label/<uuid:pk>",
        SchemeLabelTileView.as_view(),
        name="api-scheme-label-tile",
    ),
    path(
        "api/scheme/labels",
        SchemeLabelCreateView.as_view(),
        name="api-scheme-label-list-create",
    ),
    path(
        "api/scheme/<uuid:pk>/note",
        SchemeNoteView.as_view(),
        name="api-scheme-note",
    ),
    path(
        "api/scheme/<uuid:resource_id>/note/<uuid:pk>",
        SchemeNoteTileView.as_view(),
        name="api-scheme-note-tile",
    ),
    path(
        "api/scheme/note",
        SchemeNoteCreateView.as_view(),
        name="api-scheme-note-create",
    ),
    path(
        "api/scheme/<uuid:pk>/scheme-rights",
        SchemeRightsView.as_view(),
        name="api-scheme-rights",
    ),
    path(
        "api/textual-work",
        TextualWorkRdmSystemSerializerView.as_view(),
        name="api-textualwork-list",
    ),
    path(
        "api/group-rdm-system",
        GroupRdmSystemSerializerView.as_view(),
        name="api-group-list",
    ),
    path(
        "api/person-rdm-system",
        "api/person",
        PersonRdmSystemSerializerView.as_view(),
        name="api-person-list",
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
