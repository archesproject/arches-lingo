from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from arches_lingo.views.root import LingoRootView
from arches_lingo.views.api.concepts import (
    ConceptTreeView,
    ValueSearchView,
    ConceptResourceView,
    ConceptRelationshipView,
    ConceptMissingTranslationsView,
)
from arches_lingo.views.api.dashboard import DashboardStatsView
from arches_lingo.views.api.edit_log import ResourceEditLogAPIView
from arches_lingo.views.api.schemes import SchemeResourceView, SchemeLabelCountView
from arches_lingo.views.api.advanced_search import (
    AdvancedSearchView,
    AdvancedSearchOptionsView,
    ConceptSetDetailView,
    ConceptSetListView,
    ConceptSetMembersView,
    SavedSearchDetailView,
    SavedSearchListView,
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
from arches_lingo.views.api.scheme_uri_template import (
    SchemeURITemplateView,
)
from arches_lingo.views.api.settings import AppSettingsView
from arches_lingo.views.api.identifier_resolve import IdentifierResolveView
from arches_lingo.views.api.resource_list import (
    ContributorsListView,
    ResourceReferenceCountView,
    SourcesListView,
)
from arches_lingo.views.api.user_profile import (
    ChangePasswordAPIView,
    LingoUserView,
    UserProfileAPIView,
)

handler400 = "arches.app.views.main.custom_400"
handler403 = "arches.app.views.main.custom_403"
handler404 = "arches.app.views.main.custom_404"
handler500 = "arches.app.views.main.custom_500"

urlpatterns = [
    path("", LingoRootView.as_view(), name="root"),
    path("dashboard", LingoRootView.as_view(), name="dashboard"),
    path("login", LingoRootView.as_view(), name="login"),
    path("advanced-search", LingoRootView.as_view(), name="advanced-search"),
    path("schemes", LingoRootView.as_view(), name="schemes"),
    path("scheme/<uuid:id>", LingoRootView.as_view(), name="scheme"),
    path("scheme/new", LingoRootView.as_view(), name="new-scheme"),
    path("concept/<uuid:id>", LingoRootView.as_view(), name="concept"),
    path("concept/new", LingoRootView.as_view(), name="new-concept"),
    path(
        "schemes/<slug:scheme_identifier>",
        LingoRootView.as_view(),
        name="scheme-by-identifier",
    ),
    path(
        "schemes/<slug:scheme_identifier>/concepts/<slug:concept_identifier>",
        LingoRootView.as_view(),
        name="concept-by-identifier",
    ),
    path("sources", LingoRootView.as_view(), name="sources"),
    path("source/<uuid:id>", LingoRootView.as_view(), name="source"),
    path("contributors", LingoRootView.as_view(), name="contributors"),
    path("contributor/<uuid:id>", LingoRootView.as_view(), name="contributor"),
    path("profile", LingoRootView.as_view(), name="profile"),
    path(
        "api/lingo/user-profile",
        UserProfileAPIView.as_view(),
        name="api-lingo-user-profile",
    ),
    path(
        "api/lingo/user",
        LingoUserView.as_view(),
        name="api-lingo-user",
    ),
    path(
        "api/lingo/settings",
        AppSettingsView.as_view(),
        name="api-lingo-settings",
    ),
    path(
        "api/lingo/change-password",
        ChangePasswordAPIView.as_view(),
        name="api-lingo-change-password",
    ),
    path(
        "api/lingo/dashboard",
        DashboardStatsView.as_view(),
        name="api-lingo-dashboard",
    ),
    path(
        "api/lingo/concepts/missing-translations",
        ConceptMissingTranslationsView.as_view(),
        name="api-lingo-missing-translations",
    ),
    path("api/concept-tree", ConceptTreeView.as_view(), name="api-concepts"),
    path("api/search", ValueSearchView.as_view(), name="api-search"),
    path(
        "api/scheme/<uuid:scheme_resource_instance_id>/concept-identifier-counter",
        ConceptIdentifierCounterView.as_view(),
        name="api-concept-identifier-counter",
    ),
    path(
        "api/scheme/<uuid:scheme_resource_instance_id>/url-template",
        SchemeURITemplateView.as_view(),
        name="api-scheme-url-template",
    ),
    path(
        "api/lingo/scheme-resource",
        SchemeResourceView.as_view(),
        name="api-lingo-scheme-resource",
    ),
    path(
        "api/advanced-search",
        AdvancedSearchView.as_view(),
        name="api-advanced-search",
    ),
    path(
        "api/advanced-search/options",
        AdvancedSearchOptionsView.as_view(),
        name="api-advanced-search-options",
    ),
    path(
        "api/saved-searches",
        SavedSearchListView.as_view(),
        name="api-saved-searches",
    ),
    path(
        "api/saved-searches/<int:pk>",
        SavedSearchDetailView.as_view(),
        name="api-saved-search-detail",
    ),
    path(
        "api/concept-sets",
        ConceptSetListView.as_view(),
        name="api-concept-sets",
    ),
    path(
        "api/concept-sets/<int:pk>",
        ConceptSetDetailView.as_view(),
        name="api-concept-set-detail",
    ),
    path(
        "api/concept-sets/<int:pk>/members",
        ConceptSetMembersView.as_view(),
        name="api-concept-set-members",
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
        "api/lingo/schemes/<uuid:pk>",
        SchemeResourceView.as_view(),
        name="api-lingo-scheme",
    ),
    path(
        "api/lingo/resource/<uuid:resourceid>/edit-log",
        ResourceEditLogAPIView.as_view(),
        name="api-lingo-edit-log",
    ),
    path(
        "api/lingo/schemes/<uuid:pk>/label-counts",
        SchemeLabelCountView.as_view(),
        name="api-lingo-scheme-label-counts",
    ),
    path(
        "api/lingo/sources",
        SourcesListView.as_view(),
        name="api-lingo-sources",
    ),
    path(
        "api/lingo/contributors",
        ContributorsListView.as_view(),
        name="api-lingo-contributors",
    ),
    path(
        "api/lingo/resource/<uuid:resourceid>/reference-count",
        ResourceReferenceCountView.as_view(),
        name="api-lingo-resource-reference-count",
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
    path(
        "api/lingo/schemes/<slug:scheme_identifier>/resolve",
        IdentifierResolveView.as_view(),
        name="api-lingo-scheme-resolve",
    ),
    path(
        "api/lingo/schemes/<slug:scheme_identifier>/concepts/<slug:concept_identifier>/resolve",
        IdentifierResolveView.as_view(),
        name="api-lingo-concept-resolve",
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
    # Language switching is handled via the django_language cookie rather than
    # URL-based language prefixes. i18n_patterns (which would wrap all URLs with
    # a language code, e.g. /en/scheme/...) is intentionally not used, as it
    # conflicts with cookie-based switching and would break existing URL structures.
    # The i18n/ endpoint is still included to support Django's set_language view.
    urlpatterns.append(path("i18n/", include("django.conf.urls.i18n")))
