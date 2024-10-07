import os
from django.db import migrations
from django.core import management
from arches_lingo.settings import APP_ROOT
from arches_references.models import List, ListItem, ListItemValue


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0001_initial"),
        ("arches_references", "0004_require_controlledlistitem_uri"),
    ]

    def load_lists(apps, schema_editor):
        management.call_command(
            "loaddata",
            os.path.join(
                APP_ROOT,
                "pkg",
                "reference_data",
                "controlled_lists",
                "lingo_lists.json",
            ),
        )

    operations = [
        migrations.RunPython(load_lists, migrations.RunPython.noop),
    ]
