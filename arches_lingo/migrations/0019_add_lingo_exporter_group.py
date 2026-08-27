from django.db import migrations


def create_lingo_exporter_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Lingo Exporter")


def remove_lingo_exporter_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Lingo Exporter").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0018_add_related_image_gin_indexes"),
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_lingo_exporter_group, remove_lingo_exporter_group),
    ]
