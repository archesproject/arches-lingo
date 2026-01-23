import uuid
from django.db import migrations
from django.utils.translation import gettext as _


def create_standard_with_editing_resource_instance_lifecycle(apps, schema_editor):
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    ResourceInstanceLifecycle.objects.create(
        id=uuid.UUID("1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"),
        name=_("Standard (with Editing)"),
    )


def remove_standard_with_editing_resource_instance_lifecycle(apps, schema_editor):
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")
    resource_instance_lifecycle = ResourceInstanceLifecycle.objects.get(
        id="1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
    )
    resource_instance_lifecycle.delete()


def create_standard_with_editing_resource_instance_lifecycle_states(
    apps, schema_editor
):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    draft_state = ResourceInstanceLifecycleState.objects.create(
        id=uuid.UUID("0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11"),
        name=_("Draft"),
        action_label=_("Revert to Draft"),
        resource_instance_lifecycle_id=uuid.UUID(
            "1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
        ),
        is_initial_state=True,
        can_delete_resource_instances=True,
        can_edit_resource_instances=True,
    )

    active_state = ResourceInstanceLifecycleState.objects.create(
        id=uuid.UUID("6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e"),
        name=_("Active"),
        action_label=_("Make Active"),
        resource_instance_lifecycle_id=uuid.UUID(
            "1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
        ),
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=False,
    )

    editing_state = ResourceInstanceLifecycleState.objects.create(
        id=uuid.UUID("b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f"),
        name=_("Editing"),
        action_label=_("Edit"),
        resource_instance_lifecycle_id=uuid.UUID(
            "1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
        ),
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=True,
    )

    retired_state = ResourceInstanceLifecycleState.objects.create(
        id=uuid.UUID("9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c"),
        name=_("Retired"),
        action_label=_("Retire"),
        resource_instance_lifecycle_id=uuid.UUID(
            "1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
        ),
        is_initial_state=False,
        can_delete_resource_instances=False,
        can_edit_resource_instances=False,
    )

    draft_state.next_resource_instance_lifecycle_states.add(active_state)

    active_state.next_resource_instance_lifecycle_states.add(retired_state)
    retired_state.previous_resource_instance_lifecycle_states.add(active_state)

    active_state.next_resource_instance_lifecycle_states.add(editing_state)
    editing_state.previous_resource_instance_lifecycle_states.add(active_state)

    editing_state.next_resource_instance_lifecycle_states.add(active_state)
    active_state.previous_resource_instance_lifecycle_states.add(editing_state)


def remove_standard_with_editing_resource_instance_lifecycle_states(
    apps, schema_editor
):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    draft_state = ResourceInstanceLifecycleState.objects.get(
        id="0e7f8c6d-1f7b-4c2a-9a0c-2b9e0d6c8f11"
    )
    active_state = ResourceInstanceLifecycleState.objects.get(
        id="6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e"
    )
    editing_state = ResourceInstanceLifecycleState.objects.get(
        id="b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f"
    )
    retired_state = ResourceInstanceLifecycleState.objects.get(
        id="9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c"
    )

    draft_state.delete()
    active_state.delete()
    editing_state.delete()
    retired_state.delete()


def add_standard_with_editing_resource_instance_lifecycle_to_graphs(
    apps, schema_editor
):
    GraphModel = apps.get_model("models", "GraphModel")
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")

    old_standard_lifecycle = ResourceInstanceLifecycle.objects.get(
        id="7e3cce56-fbfb-4a4b-8e83-59b9f9e7cb75"
    )
    new_lifecycle = ResourceInstanceLifecycle.objects.get(
        id="1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
    )

    target_slugs = ["scheme", "concept"]

    for graph_model in GraphModel.objects.filter(slug__in=target_slugs):
        if (
            graph_model.isresource
            and graph_model.resource_instance_lifecycle_id == old_standard_lifecycle.id
        ):
            graph_model.resource_instance_lifecycle = new_lifecycle
            graph_model.save()


def remove_standard_with_editing_resource_instance_lifecycle_from_graphs(
    apps, schema_editor
):
    GraphModel = apps.get_model("models", "GraphModel")
    ResourceInstanceLifecycle = apps.get_model("models", "ResourceInstanceLifecycle")

    old_standard_lifecycle = ResourceInstanceLifecycle.objects.get(
        id="7e3cce56-fbfb-4a4b-8e83-59b9f9e7cb75"
    )
    new_lifecycle = ResourceInstanceLifecycle.objects.get(
        id="1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21"
    )

    target_slugs = ["scheme", "concept"]

    for graph_model in GraphModel.objects.filter(slug__in=target_slugs):
        if (
            graph_model.isresource
            and graph_model.resource_instance_lifecycle_id == new_lifecycle.id
        ):
            graph_model.resource_instance_lifecycle = old_standard_lifecycle
            graph_model.save()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0003_add_concept_identifier_counters"),
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
