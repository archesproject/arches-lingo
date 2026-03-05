from django.db import migrations


FUNCTION_ID = "dc0a3a78-f8a3-4472-b77d-7301d6718a36"


def forward(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.update_or_create(
        functionid=FUNCTION_ID,
        defaults={
            "modulename": "reciprocal_relationship.py",
            "classname": "ReciprocalRelationshipFunction",
            "functiontype": "node",
            "name": "Reciprocal Relationship",
            "description": "Ensures reciprocal relationship tiles exist between related Concepts",
            "defaultconfig": {
                "triggering_nodegroups": [],
            },
            "component": "",
        },
    )


def reverse(apps, schema_editor):
    Function = apps.get_model("models", "Function")
    Function.objects.filter(functionid=FUNCTION_ID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0005_advanced_search_models"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
