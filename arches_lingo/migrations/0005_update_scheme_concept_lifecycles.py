import uuid
from django.db import migrations
from django.utils.translation import gettext as _


NEW_LIFECYCLE_ID = uuid.UUID("1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21")
OLD_STANDARD_LIFECYCLE_ID = uuid.UUID("7e3cce56-fbfb-4a4b-8e83-59b9f9e7cb75")

DRAFT_STATE_ID = uuid.UUID("0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11")
PUBLISHED_STATE_ID = uuid.UUID("6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e")
EDITING_STATE_ID = uuid.UUID("b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f")
RETIRED_STATE_ID = uuid.UUID("9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c")


def create_standard_with_editing_resource_instance_lifecycle(apps, schema_editor):
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    ResourceInstanceLifecycle.objects.create(
        id=NEW_LIFECYCLE_ID,
        name=_("Standard (with Editing)"),
    )


def remove_standard_with_editing_resource_instance_lifecycle(apps, schema_editor):
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    resource_instance_lifecycle = ResourceInstanceLifecycle.objects.get(
        id=NEW_LIFECYCLE_ID
    )
    resource_instance_lifecycle.delete()


def create_standard_with_editing_resource_instance_lifecycle_states(
    apps, schema_editor
):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    draft_state = ResourceInstanceLifecycleState.objects.create(
        id=DRAFT_STATE_ID,
        name=_("Draft"),
        action_label=_("Revert to Draft"),
        resource_instance_lifecycle_id=NEW_LIFECYCLE_ID,
        is_initial_state=True,
        can_delete_resource_instances=True,
        can_edit_resource_instances=True,
    )

    published_state = ResourceInstanceLifecycleState.objects.create(
        id=PUBLISHED_STATE_ID,
        name=_("Published"),
        action_label=_("Publish"),
        resource_instance_lifecycle_id=NEW_LIFECYCLE_ID,
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=False,
    )

    editing_state = ResourceInstanceLifecycleState.objects.create(
        id=EDITING_STATE_ID,
        name=_("Editing"),
        action_label=_("Edit"),
        resource_instance_lifecycle_id=NEW_LIFECYCLE_ID,
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=True,
    )

    retired_state = ResourceInstanceLifecycleState.objects.create(
        id=RETIRED_STATE_ID,
        name=_("Retired"),
        action_label=_("Retire"),
        resource_instance_lifecycle_id=NEW_LIFECYCLE_ID,
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=False,
    )

    draft_state.next_resource_instance_lifecycle_states.add(published_state)

    published_state.next_resource_instance_lifecycle_states.add(retired_state)
    retired_state.previous_resource_instance_lifecycle_states.add(published_state)

    published_state.next_resource_instance_lifecycle_states.add(editing_state)
    editing_state.previous_resource_instance_lifecycle_states.add(published_state)

    editing_state.next_resource_instance_lifecycle_states.add(published_state)
    published_state.previous_resource_instance_lifecycle_states.add(editing_state)


def remove_standard_with_editing_resource_instance_lifecycle_states(
    apps, schema_editor
):
    ResourceInstance = apps.get_model("models", "ResourceInstance")
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    default_old_state = ResourceInstanceLifecycleState.objects.get(
        resource_instance_lifecycle_id=OLD_STANDARD_LIFECYCLE_ID,
        is_initial_state=True,
    )

    ResourceInstance.objects.filter(
        resource_instance_lifecycle_state_id__in=[
            DRAFT_STATE_ID,
            PUBLISHED_STATE_ID,
            EDITING_STATE_ID,
            RETIRED_STATE_ID,
        ]
    ).update(resource_instance_lifecycle_state=default_old_state)

    draft_state = ResourceInstanceLifecycleState.objects.get(id=DRAFT_STATE_ID)
    published_state = ResourceInstanceLifecycleState.objects.get(id=PUBLISHED_STATE_ID)
    editing_state = ResourceInstanceLifecycleState.objects.get(id=EDITING_STATE_ID)
    retired_state = ResourceInstanceLifecycleState.objects.get(id=RETIRED_STATE_ID)

    draft_state.delete()
    published_state.delete()
    editing_state.delete()
    retired_state.delete()


def add_standard_with_editing_resource_instance_lifecycle_to_graphs(
    apps, schema_editor
):
    GraphModel = apps.get_model("models", "GraphModel")
    ResourceInstance = apps.get_model("models", "ResourceInstance")
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    old_standard_lifecycle = ResourceInstanceLifecycle.objects.get(
        id=OLD_STANDARD_LIFECYCLE_ID
    )
    new_lifecycle = ResourceInstanceLifecycle.objects.get(id=NEW_LIFECYCLE_ID)

    new_initial_state = ResourceInstanceLifecycleState.objects.get(
        resource_instance_lifecycle_id=new_lifecycle.id,
        is_initial_state=True,
    )

    target_slugs = ["scheme", "concept"]

    target_graph_ids = list(
        GraphModel.objects.filter(
            slug__in=target_slugs,
            isresource=True,
            resource_instance_lifecycle_id=old_standard_lifecycle.id,
        ).values_list("graphid", flat=True)
    )

    GraphModel.objects.filter(graphid__in=target_graph_ids).update(
        resource_instance_lifecycle=new_lifecycle
    )

    ResourceInstance.objects.filter(
        graph_id__in=target_graph_ids,
        resource_instance_lifecycle_state__resource_instance_lifecycle_id=old_standard_lifecycle.id,
    ).update(resource_instance_lifecycle_state=new_initial_state)


def remove_standard_with_editing_resource_instance_lifecycle_from_graphs(
    apps, schema_editor
):
    GraphModel = apps.get_model("models", "GraphModel")
    ResourceInstance = apps.get_model("models", "ResourceInstance")
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    old_standard_lifecycle = ResourceInstanceLifecycle.objects.get(
        id=OLD_STANDARD_LIFECYCLE_ID
    )
    new_lifecycle = ResourceInstanceLifecycle.objects.get(id=NEW_LIFECYCLE_ID)

    old_initial_state = ResourceInstanceLifecycleState.objects.get(
        resource_instance_lifecycle_id=old_standard_lifecycle.id,
        is_initial_state=True,
    )

    target_slugs = ["scheme", "concept"]

    target_graph_ids = list(
        GraphModel.objects.filter(
            slug__in=target_slugs,
            isresource=True,
            resource_instance_lifecycle_id=new_lifecycle.id,
        ).values_list("graphid", flat=True)
    )

    ResourceInstance.objects.filter(
        graph_id__in=target_graph_ids,
        resource_instance_lifecycle_state__resource_instance_lifecycle_id=new_lifecycle.id,
    ).update(resource_instance_lifecycle_state=old_initial_state)

    GraphModel.objects.filter(graphid__in=target_graph_ids).update(
        resource_instance_lifecycle=old_standard_lifecycle
    )


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0004_add_concept_identifier_counters"),
    ]

    operations = [
        migrations.RunPython(
            create_standard_with_editing_resource_instance_lifecycle,
            remove_standard_with_editing_resource_instance_lifecycle,
        ),
        migrations.RunPython(
            create_standard_with_editing_resource_instance_lifecycle_states,
            remove_standard_with_editing_resource_instance_lifecycle_states,
        ),
        migrations.RunPython(
            add_standard_with_editing_resource_instance_lifecycle_to_graphs,
            remove_standard_with_editing_resource_instance_lifecycle_from_graphs,
        ),
    ]
