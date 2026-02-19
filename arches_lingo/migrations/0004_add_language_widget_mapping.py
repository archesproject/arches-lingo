from django.db import migrations
from arches_component_lab.utils.widget_synchronizer import WidgetSynchronizer


class Migration(migrations.Migration):

    dependencies = [
        ("models", "12557_add_language_datatype"),
        ("arches_lingo", "0003_add_languages"),
        ("arches_component_lab", "0003_add_pk_default"),
    ]

    def forward(apps, schema_editor):
        WidgetSynchronizer().synchronize_widgets(
            "language-widget", "LanguageSelectWidget"
        )

    def reverse(apps, schema_editor):
        Widget = apps.get_model("arches", "Widget")
        WidgetMapping = apps.get_model("arches_component_lab", "WidgetMapping")
        lang_widget = Widget.objects.get(name="language-widget")
        WidgetMapping.objects.filter(widget=lang_widget).delete()

    operations = [
        migrations.RunPython(forward, reverse),
    ]
