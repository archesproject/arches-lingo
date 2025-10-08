from arches_controlled_lists.management.commands.packages import (
    Command as PackagesCommand,
)
from arches_lingo.utils.skos import SKOSReader


class Command(PackagesCommand):

    def add_arguments(self, parser):
        super().add_arguments(parser)

        idx_of_operation_arg = [a.dest for a in parser._actions].index("operation")
        parser._actions[idx_of_operation_arg].choices.extend(["import_lingo_resources"])

    def handle(self, *args, **options):
        super().handle(self, *args, **options)

        if options["operation"] == "import_lingo_resources":
            self.import_lingo_resources(options["source"], options["overwrite"])

    def import_lingo_resources(self, source, overwrite_options):
        skos = SKOSReader()
        rdf = skos.read_file(source)
        skos.save_lingo_resources_from_skos(rdf, overwrite_options=overwrite_options)
