import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0015_add_retired_to_editing_lifecycle_transition"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchemeAttribution",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "attribution",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "scheme",
                    models.OneToOneField(
                        db_column="scheme_resource_instance_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scheme_attribution",
                        to="models.resourceinstance",
                    ),
                ),
            ],
            options={
                "db_table": "scheme_attributions",
            },
        ),
    ]
