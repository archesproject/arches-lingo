from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("models", "12557_add_language_datatype"),
        ("arches_lingo", "0003_add_languages"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
