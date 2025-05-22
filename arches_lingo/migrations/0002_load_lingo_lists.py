import io
import os

from django.core import management
from django.db import migrations

from arches_lingo.settings import APP_ROOT


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0001_initial"),
        ("arches_controlled_lists", "0001_initial"),
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
            stdout=io.StringIO(),
        )

    operations = [
        migrations.RunPython(load_lists, migrations.RunPython.noop),
    ]
