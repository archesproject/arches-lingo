import uuid
import os
import io
from django.core.files.uploadedfile import InMemoryUploadedFile
from arches.app.models import models
from arches_controlled_lists.management.commands.packages import (
    Command as PackagesCommand,
)
from arches_lingo.etl_modules.migrate_to_lingo import LingoResourceImporter
from arches_lingo.utils.skos import load_pinned_resource_ids


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
        parser.add_argument(
            "--pin-resource-ids",
            type=str,
            default="",
            help=(
                "Path to a CSV of subject_uri,resourceinstanceid pairs. Resources "
                "listed there keep the id given rather than being assigned a new "
                "one, so a re-import leaves surviving resources on their existing "
                "ids. Subjects not listed are assigned new ids as usual."
            ),
        )

    def handle(self, *args, **options):
        super().handle(self, *args, **options)

        if options["operation"] == "import_lingo_resources":
            self.import_lingo_resources(
                options["source"],
                options["overwrite"],
                import_identifiers=options["import_identifiers"],
                namespace_template=options["namespace_template"],
                pin_resource_ids=options["pin_resource_ids"],
            )

    def import_lingo_resources(
        self,
        source,
        overwrite_options,
        import_identifiers=False,
        namespace_template="",
        pin_resource_ids="",
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

        pinned_resource_ids = {}
        if pin_resource_ids:
            pinned_resource_ids = load_pinned_resource_ids(pin_resource_ids)
            self.stdout.write(
                f"Pinning {len(pinned_resource_ids):,} resource ids from "
                f"{pin_resource_ids}"
            )

        self.loadid = str(uuid.uuid4())
        bulk_loader = LingoResourceImporter(
            loadid=self.loadid,
            userid=models.User.objects.get(username="admin").pk,
            mode="cli",
            import_identifiers=import_identifiers,
            namespace_template=namespace_template,
            pinned_resource_ids=pinned_resource_ids,
        )
        start_request = bulk_loader.start(request=None)
        bulk_loader.file = inmemory_file
        # Avoid using celery for package import
        # Keep the package import in-process regardless of file size. Above
        # this limit the importer defers to a celery worker, which both
        # requires a running worker and would not carry the pinned-id map.
        # The converted AAT export is already ~86 MB, so the previous 90 MB
        # limit left almost no headroom.
        bulk_loader.config["celeryByteSizeLimit"] = 2_000_000_000  # 2 GB
        write_request = bulk_loader.write(request=None)
