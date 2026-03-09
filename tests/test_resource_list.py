from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.test.utils import captured_stdout
from django.urls import reverse

from arches.app.models.models import GraphModel, ResourceInstance
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from arches.app.utils.data_management.resource_graphs.importer import (
    import_graph as ResourceGraphImporter,
)

from arches_lingo.utils.resource_list import (
    CONTRIBUTORS_GRAPH_SLUGS,
    SOURCES_GRAPH_SLUGS,
    get_paginated_resources,
)


class ResourceListTests(TestCase):
    graph_fixtures = [
        "person_system.json",
        "group_system.json",
        "textual_work_system.json",
    ]

    @classmethod
    def load_ontology(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "ontologies" / "takin"
        management.call_command("load_ontology", source=path, verbosity=0)

    @classmethod
    def load_graphs(cls):
        path = Path(settings.APP_ROOT) / "pkg" / "graphs" / "resource_models"
        for file_path in cls.graph_fixtures:
            with captured_stdout(), open(path / file_path, "r") as graph_file:
                archesfile = JSONDeserializer().deserialize(graph_file)
                ResourceGraphImporter(archesfile["graph"], overwrite_graphs=True)

    @classmethod
    def setUpTestData(cls):
        cls.load_ontology()
        cls.load_graphs()
        cls.admin = User.objects.get(username="admin")

        cls.person_graph = GraphModel.objects.get(slug="person_system")
        cls.group_graph = GraphModel.objects.get(slug="group")
        cls.textual_work_graph = GraphModel.objects.get(slug="textual_work")

        cls.person_alice = ResourceInstance.objects.create(
            graph=cls.person_graph, name="Alice Smith"
        )
        cls.person_bob = ResourceInstance.objects.create(
            graph=cls.person_graph, name="Bob Jones"
        )
        cls.group_archivists = ResourceInstance.objects.create(
            graph=cls.group_graph, name="Archivists Guild"
        )
        cls.source_book = ResourceInstance.objects.create(
            graph=cls.textual_work_graph, name="A Great Book"
        )
        cls.source_article = ResourceInstance.objects.create(
            graph=cls.textual_work_graph, name="Important Article"
        )
        cls.source_paper = ResourceInstance.objects.create(
            graph=cls.textual_work_graph, name="Research Paper"
        )


class TestGetPaginatedResources(ResourceListTests):
    def test_sources_returns_textual_work_resources(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS)
        self.assertEqual(result["count"], 3)
        display_names = [r["display_name"] for r in result["results"]]
        self.assertIn("A Great Book", display_names)
        self.assertIn("Important Article", display_names)
        self.assertIn("Research Paper", display_names)

    def test_contributors_returns_person_and_group_resources(self):
        result = get_paginated_resources(CONTRIBUTORS_GRAPH_SLUGS)
        self.assertEqual(result["count"], 3)
        graph_slugs = {r["graph_slug"] for r in result["results"]}
        self.assertIn("person_system", graph_slugs)
        self.assertIn("group", graph_slugs)

    def test_search_filters_by_name(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS, search_term="Great")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["display_name"], "A Great Book")

    def test_search_is_case_insensitive(self):
        result = get_paginated_resources(CONTRIBUTORS_GRAPH_SLUGS, search_term="alice")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["display_name"], "Alice Smith")

    def test_pagination_with_limit_and_offset(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS, limit=2, offset=0)
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["results"]), 2)

    def test_pagination_offset_past_end(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS, limit=25, offset=100)
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["results"]), 0)

    def test_results_ordered_by_name(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS)
        display_names = [r["display_name"] for r in result["results"]]
        self.assertEqual(display_names, sorted(display_names))

    def test_result_includes_graph_metadata(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS)
        for resource_summary in result["results"]:
            self.assertIn("resourceinstanceid", resource_summary)
            self.assertIn("display_name", resource_summary)
            self.assertIn("graph_slug", resource_summary)
            self.assertIn("graph_name", resource_summary)
            self.assertEqual(resource_summary["graph_slug"], "textual_work")

    def test_empty_search_returns_all(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS, search_term="")
        self.assertEqual(result["count"], 3)

    def test_no_match_returns_empty(self):
        result = get_paginated_resources(SOURCES_GRAPH_SLUGS, search_term="xyz_nomatch")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])


class TestSourcesListView(ResourceListTests):
    def test_sources_list_requires_authentication(self):
        response = self.client.get(reverse("api-lingo-sources"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_sources_list_returns_paginated_results(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-lingo-sources"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 3)

    def test_sources_list_filters_by_search(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-lingo-sources"), {"search": "Great"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_sources_list_paginates(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("api-lingo-sources"), {"limit": "2", "offset": "0"}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 2)


class TestContributorsListView(ResourceListTests):
    def test_contributors_list_requires_authentication(self):
        response = self.client.get(reverse("api-lingo-contributors"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_contributors_list_returns_paginated_results(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-lingo-contributors"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 3)

    def test_contributors_includes_both_persons_and_groups(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("api-lingo-contributors"))
        data = response.json()
        graph_slugs = {r["graph_slug"] for r in data["results"]}
        self.assertIn("person_system", graph_slugs)
        self.assertIn("group", graph_slugs)

    def test_contributors_list_filters_by_search(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("api-lingo-contributors"), {"search": "Archivists"}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["graph_slug"], "group")
