import uuid

from django.db import migrations


FUNCTION_ID = uuid.UUID("9f2f7d36-7a62-4a33-9f27-9a4b9e4a8d2a")


def register_update_concept_lifecycle_states_for_scheme_function(apps, schema_editor):
    function_model = apps.get_model("models", "Function")
    graph_model = apps.get_model("models", "GraphModel")
    function_x_graph_model = apps.get_model("models", "FunctionXGraph")

    function_instance, created = function_model.objects.update_or_create(
        functionid=FUNCTION_ID,
        defaults={
            "name": "Update Concept Lifecycle States For Scheme",
            "functiontype": "lifecyclehandler",
            "description": "Updates concept lifecycle state tiles for all concepts in a scheme.",
            "defaultconfig": {},
            "component": "",
            "modulename": "update_concept_lifecycle_states_for_scheme.py",
            "classname": "UpdateConceptLifecycleStatesForScheme",
        },
    )

    scheme_graph_instance = graph_model.objects.get(slug="scheme")

    function_x_graph_model.objects.update_or_create(
        function=function_instance,
        graph=scheme_graph_instance,
        defaults={
            "config": {},
        },
    )


def unregister_update_concept_lifecycle_states_for_scheme_function(apps, schema_editor):
    function_model = apps.get_model("models", "Function")
    function_x_graph_model = apps.get_model("models", "FunctionXGraph")

    function_x_graph_model.objects.filter(
        function_id=FUNCTION_ID,
        graph__slug="scheme",
    ).delete()

    function_model.objects.filter(functionid=FUNCTION_ID).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("arches_lingo", "0004_update_scheme_concept_lifecycles"),
    ]

    operations = [
        migrations.RunPython(
            register_update_concept_lifecycle_states_for_scheme_function,
            unregister_update_concept_lifecycle_states_for_scheme_function,
        ),
    ]
