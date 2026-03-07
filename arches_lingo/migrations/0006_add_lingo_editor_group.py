from django.db import migrations


def create_lingo_editor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Lingo Editor")


def remove_lingo_editor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Lingo Editor").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0005_reciprocal_relationship_function"),
    ]

    operations = [
        migrations.RunPython(create_lingo_editor_group, remove_lingo_editor_group),
    ]
