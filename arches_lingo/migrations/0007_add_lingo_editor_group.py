from django.db import migrations


def create_lingo_editor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Lingo Editor")

    schema_editor.execute(
        """
        insert into guardian_groupobjectpermission (
            "object_pk",
            "content_type_id",
            "group_id",
            "permission_id"
        )
        select 
            etl_modules.etlmoduleid as object_pk,
            dct.id as content_type_id,
            ag.id as group_id,
            ap.id as permission_id
        from etl_modules
        join django_content_type dct on dct.model = 'etlmodule'
        join auth_group ag on ag.name = 'Lingo Editor'
        join auth_permission ap on ap.codename = 'view_etlmodule'
        where etl_modules.slug in ('migrate-to-lingo', 'export-lingo-resources');
        """
    )


def remove_lingo_editor_group(apps, schema_editor):
    schema_editor.execute(
        """
        DELETE FROM guardian_groupobjectpermission
        WHERE 
            object_pk IN (
                SELECT etlmoduleid::text 
                FROM etl_modules 
                WHERE slug IN ('migrate-to-lingo', 'export-lingo-resources')
            )
            AND permission_id = (
                SELECT id 
                FROM auth_permission 
                WHERE codename = 'view_etlmodule'
            )
            AND group_id = (
                SELECT id 
                FROM auth_group 
                WHERE name = 'Lingo Editor'
            );
        """
    )

    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Lingo Editor").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("arches_lingo", "0006_advanced_search_models"),
    ]

    operations = [
        migrations.RunPython(create_lingo_editor_group, remove_lingo_editor_group),
    ]
