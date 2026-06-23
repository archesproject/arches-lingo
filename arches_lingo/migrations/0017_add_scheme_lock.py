import uuid

from django.db import migrations

LOCKED_STATE_ID = uuid.UUID("c9f7e3d1-2a5b-4c8d-9e6f-3b0a1d2e4f7c")
PUBLISHED_STATE_ID = uuid.UUID("6b0f1a7b-5b3d-4b2a-8a5b-7c3a1b0f2d9e")
EDITING_STATE_ID = uuid.UUID("b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f")
LINGO_LIFECYCLE_ID = uuid.UUID("1c9b0c18-3a3a-4e6c-ae3b-5f3c5b9f6a21")


def create_locked_state_and_admin_group(apps, schema_editor):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )
    Group = apps.get_model("auth", "Group")

    locked_state, _ = ResourceInstanceLifecycleState.objects.get_or_create(
        id=LOCKED_STATE_ID,
        defaults={
            "name": "Locked",
            "action_label": "Lock",
            "is_initial_state": False,
            "can_edit_resource_instances": False,
            "can_delete_resource_instances": False,
            "resource_instance_lifecycle_id": LINGO_LIFECYCLE_ID,
        },
    )

    published_state = ResourceInstanceLifecycleState.objects.get(id=PUBLISHED_STATE_ID)
    editing_state = ResourceInstanceLifecycleState.objects.get(id=EDITING_STATE_ID)

    published_state.next_resource_instance_lifecycle_states.add(locked_state)
    locked_state.previous_resource_instance_lifecycle_states.add(published_state)

    editing_state.next_resource_instance_lifecycle_states.add(locked_state)
    locked_state.previous_resource_instance_lifecycle_states.add(editing_state)

    Group.objects.get_or_create(name="Lingo Admin")


def remove_locked_state_and_admin_group(apps, schema_editor):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )
    Group = apps.get_model("auth", "Group")

    try:
        locked_state = ResourceInstanceLifecycleState.objects.get(id=LOCKED_STATE_ID)
        published_state = ResourceInstanceLifecycleState.objects.get(
            id=PUBLISHED_STATE_ID
        )
        editing_state = ResourceInstanceLifecycleState.objects.get(id=EDITING_STATE_ID)

        published_state.next_resource_instance_lifecycle_states.remove(locked_state)
        locked_state.previous_resource_instance_lifecycle_states.remove(published_state)

        editing_state.next_resource_instance_lifecycle_states.remove(locked_state)
        locked_state.previous_resource_instance_lifecycle_states.remove(editing_state)

        ResourceInstance = apps.get_model("models", "ResourceInstance")
        ResourceInstance.objects.filter(
            resource_instance_lifecycle_state=locked_state
        ).update(resource_instance_lifecycle_state=editing_state)

        locked_state.delete()
    except ResourceInstanceLifecycleState.DoesNotExist:
        pass

    Group.objects.filter(name="Lingo Admin").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0016_add_scheme_attribution"),
        ("models", "0001_initial"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_locked_state_and_admin_group,
            remove_locked_state_and_admin_group,
        ),
    ]
