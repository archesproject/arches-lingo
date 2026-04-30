import uuid
import os
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from arches.app.models import models
from arches_controlled_lists.management.commands.packages import (
    Command as PackagesCommand,
)
from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter


class Command(PackagesCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)

        idx_of_operation_arg = [a.dest for a in parser._actions].index("operation")
        parser._actions[idx_of_operation_arg].choices.extend(["import_lingo_resources"])

        parser.add_argument(
            "--import-identifiers",
            action="store_true",
            default=False,
            help="Import identifiers as URI/Identifier tiles and assign lifecycle states",
        )
        parser.add_argument(
            "--namespace-template",
            type=str,
            default="",
            help="Namespace URL template for the scheme (requires --import-identifiers)",
        )

    def handle(self, *args, **options):
        super().handle(self, *args, **options)

        if options["operation"] == "import_lingo_resources":
            self.import_lingo_resources(
                options["source"],
                options["overwrite"],
                import_identifiers=options["import_identifiers"],
                namespace_template=options["namespace_template"],
            )

    def import_lingo_resources(
        self, source, overwrite_options, import_identifiers=False, namespace_template=""
    ):
        file_name = os.path.basename(source)
        with open(source, "rb") as f:
            file_data = f.read()
        inmemory_file = InMemoryUploadedFile(
            file=io.BytesIO(file_data),
            field_name="file",
            name=file_name,
            content_type="application/xml",
            size=len(file_data),
            charset=None,
        )

        self.loadid = str(uuid.uuid4())
        bulk_loader = LingoResourceImporter(
            loadid=self.loadid,
            userid=models.User.objects.get(username="admin").pk,
            mode="cli",
            import_identifiers=import_identifiers,
            namespace_template=namespace_template,
        )
        start_request = bulk_loader.start(request=None)
        bulk_loader.file = inmemory_file
        # Avoid using celery for package import
        bulk_loader.config["celeryByteSizeLimit"] = 90000000  # 90mb
        write_request = bulk_loader.write(request=None)
