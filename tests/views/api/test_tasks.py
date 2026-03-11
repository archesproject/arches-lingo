import uuid
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from arches.app.models.models import ETLModule, LoadEvent

from arches_lingo.const import RESOURCE_EDITOR_GROUP_NAME
from arches_lingo.utils.tasks import (
    cancel_user_load_event,
    delete_user_load_event,
    get_user_load_events,
)

# These tests can be run from the command line via:
# python manage.py test tests.views.api.test_tasks --settings="tests.test_settings"


def create_etl_module():
    return ETLModule.objects.create(
        name="Test Module",
        icon="fa fa-upload",
        etl_type="import",
        component="views/components/etl_modules/import",
        componentname="import",
        slug=f"test-module-{uuid.uuid4().hex[:8]}",
    )


def create_load_event(
    user, etl_module, complete=False, successful=None, status="running"
):
    return LoadEvent.objects.create(
        user=user,
        etl_module=etl_module,
        complete=complete,
        successful=successful,
        status=status,
        load_description="Test load",
    )


class TaskUtilsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="owner", password="pass")
        cls.other_user = User.objects.create_user(username="other", password="pass")
        cls.etl_module = create_etl_module()

    def test_get_user_load_events_returns_only_own_events(self):
        own_event = create_load_event(
            self.owner,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )
        create_load_event(
            self.other_user,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )

        result = get_user_load_events(self.owner)
        loadids = [e["loadid"] for e in result["events"]]

        self.assertIn(str(own_event.loadid), loadids)
        self.assertEqual(len(loadids), 1)

    def test_get_user_load_events_pagination_metadata(self):
        result = get_user_load_events(self.owner, page=1)
        self.assertIn("paginator", result)
        self.assertIn("total", result["paginator"])
        self.assertIn("total_pages", result["paginator"])
        self.assertIn("current_page", result["paginator"])

    def test_cancel_user_load_event_not_found_returns_failure(self):
        result = cancel_user_load_event(self.owner, str(uuid.uuid4()))
        self.assertFalse(result["success"])

    def test_cancel_user_load_event_owned_by_other_user_returns_failure(self):
        other_event = create_load_event(self.other_user, self.etl_module)

        result = cancel_user_load_event(self.owner, str(other_event.loadid))
        self.assertFalse(result["success"])

    def test_cancel_user_load_event_already_complete_returns_failure(self):
        completed_event = create_load_event(
            self.owner,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )

        result = cancel_user_load_event(self.owner, str(completed_event.loadid))
        self.assertFalse(result["success"])

    @patch(
        "arches_lingo.utils.tasks.task_management.check_if_celery_available",
        return_value=False,
    )
    def test_cancel_user_load_event_without_celery_returns_failure(self, _mock):
        running_event = create_load_event(self.owner, self.etl_module)

        result = cancel_user_load_event(self.owner, str(running_event.loadid))
        self.assertFalse(result["success"])

    def test_delete_user_load_event_not_found_returns_failure(self):
        result = delete_user_load_event(self.owner, str(uuid.uuid4()))
        self.assertFalse(result["success"])

    def test_delete_user_load_event_owned_by_other_user_returns_failure(self):
        other_event = create_load_event(
            self.other_user,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )

        result = delete_user_load_event(self.owner, str(other_event.loadid))
        self.assertFalse(result["success"])

    def test_delete_user_load_event_still_running_returns_failure(self):
        running_event = create_load_event(self.owner, self.etl_module, complete=False)

        result = delete_user_load_event(self.owner, str(running_event.loadid))
        self.assertFalse(result["success"])

    def test_delete_user_load_event_completed_succeeds(self):
        completed_event = create_load_event(
            self.owner,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )

        result = delete_user_load_event(self.owner, str(completed_event.loadid))
        self.assertTrue(result["success"])
        self.assertFalse(
            LoadEvent.objects.filter(loadid=completed_event.loadid).exists()
        )

    def test_delete_user_load_event_cancelled_succeeds(self):
        cancelled_event = create_load_event(
            self.owner, self.etl_module, complete=False, status="cancelled"
        )

        result = delete_user_load_event(self.owner, str(cancelled_event.loadid))
        self.assertTrue(result["success"])
        self.assertFalse(
            LoadEvent.objects.filter(loadid=cancelled_event.loadid).exists()
        )


class UserTaskListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resource_editor_group = Group.objects.get_or_create(
            name=RESOURCE_EDITOR_GROUP_NAME
        )[0]
        cls.editor = User.objects.create_user(
            username="resourceeditor", password="pass"
        )
        cls.editor.groups.add(cls.resource_editor_group)
        cls.non_editor = User.objects.create_user(username="readonly", password="pass")
        cls.etl_module = create_etl_module()

    def test_list_tasks_requires_resource_editor(self):
        self.client.force_login(self.non_editor)
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.get(reverse("api-lingo-tasks"))
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_list_tasks_returns_only_own_events(self):
        other_user = User.objects.create_user(username="othereditor", password="pass")
        other_user.groups.add(self.resource_editor_group)
        own_event = create_load_event(
            self.editor,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )
        create_load_event(
            other_user,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )

        self.client.force_login(self.editor)
        response = self.client.get(reverse("api-lingo-tasks"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        data = response.json()
        loadids = [e["loadid"] for e in data["events"]]
        self.assertIn(str(own_event.loadid), loadids)
        self.assertEqual(len(loadids), 1)

    def test_delete_task_requires_resource_editor(self):
        own_event = create_load_event(
            self.editor,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )
        self.client.force_login(self.non_editor)
        with self.assertLogs("django.request", level="WARNING"):
            response = self.client.delete(
                reverse(
                    "api-lingo-task-detail", kwargs={"loadid": str(own_event.loadid)}
                )
            )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_delete_completed_task_succeeds(self):
        own_event = create_load_event(
            self.editor,
            self.etl_module,
            complete=True,
            successful=True,
            status="complete",
        )
        self.client.force_login(self.editor)
        response = self.client.delete(
            reverse("api-lingo-task-detail", kwargs={"loadid": str(own_event.loadid)})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(LoadEvent.objects.filter(loadid=own_event.loadid).exists())
