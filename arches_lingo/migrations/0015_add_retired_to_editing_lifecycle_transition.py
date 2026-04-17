import uuid
from django.db import migrations


EDITING_STATE_ID = uuid.UUID("b3a6a0d2-2b5c-4c2f-9d6c-0c2a5b7d1e8f")
RETIRED_STATE_ID = uuid.UUID("9d2e1c0b-7a6b-4b3d-8c1a-0f2d9e6b0a7c")


def add_lifecycle_transitions(apps, schema_editor):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    retired_state = ResourceInstanceLifecycleState.objects.get(id=RETIRED_STATE_ID)
    editing_state = ResourceInstanceLifecycleState.objects.get(id=EDITING_STATE_ID)

    editing_state.next_resource_instance_lifecycle_states.add(retired_state)
    retired_state.previous_resource_instance_lifecycle_states.add(editing_state)

    retired_state.next_resource_instance_lifecycle_states.add(editing_state)
    editing_state.previous_resource_instance_lifecycle_states.add(retired_state)


def remove_lifecycle_transitions(apps, schema_editor):
    ResourceInstanceLifecycleState = apps.get_model(
        "models", "ResourceInstanceLifecycleState"
    )

    retired_state = ResourceInstanceLifecycleState.objects.get(id=RETIRED_STATE_ID)
    editing_state = ResourceInstanceLifecycleState.objects.get(id=EDITING_STATE_ID)

    editing_state.next_resource_instance_lifecycle_states.remove(retired_state)
    retired_state.previous_resource_instance_lifecycle_states.remove(editing_state)

    retired_state.next_resource_instance_lifecycle_states.remove(editing_state)
    editing_state.previous_resource_instance_lifecycle_states.remove(retired_state)


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0014_add_attribution_gin_indexes"),
    ]

    operations = [
        migrations.RunPython(
            add_lifecycle_transitions,
            remove_lifecycle_transitions,
        ),
    ]
