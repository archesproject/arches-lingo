from copy import deepcopy

from django.contrib.postgres.fields import ArrayField
from django.db.models import fields, ForeignKey, DO_NOTHING
from rest_framework import renderers
from rest_framework import serializers
from rest_framework.utils import model_meta

from arches.app.models.models import ResourceInstance, Node
from arches.app.utils.betterJSONSerializer import JSONSerializer


# Work around I18n_string stuff
renderers.JSONRenderer.encoder_class = JSONSerializer
renderers.JSONOpenAPIRenderer.encoder_class = JSONSerializer


class PythonicModelSerializer(serializers.ModelSerializer):
    # TODO: move into core / or arches-rest-framework?
    DATATYPE_FIELD_MAPPING = {
        "string": fields.CharField(),  # XXX
        "number": fields.FloatField(),
        "concept": fields.CharField(),
        "concept-list": ArrayField(base_field=fields.CharField()),
        "date": fields.CharField(),  # XXX
        "node-value": fields.CharField(),  # XXX
        "edtf": fields.CharField(),  # XXX
        "annotation": fields.CharField(),  # XXX
        "url": fields.URLField(),
        "resource-instance": ForeignKey(to="self", on_delete=DO_NOTHING),
        "resource-instance-list": ArrayField(base_field=fields.UUIDField()),  # XXX
        "boolean": fields.BooleanField(),
        "domain-value": ArrayField(base_field=fields.CharField()),
        "domain-value-list": ArrayField(base_field=fields.CharField()),
        "non-localized-string": fields.CharField(),
        "geojson-feature-collection": fields.CharField(),  # XXX
        "file-list": ArrayField(base_field=fields.CharField()),  # XXX
        # "reference"
    }

    def get_default_field_names(self, declared_fields, model_info):
        field_names = super().get_default_field_names(declared_fields, model_info)
        aliases = self.__class__.Meta.fields
        if aliases == "__all__":
            aliases = (
                Node.objects.filter(
                    graph__slug=self.__class__.Meta.graph_slug,
                    graph__source_identifier=None,
                )
                .exclude(nodegroup=None)
                .exclude(datatype="semantic")
                .values_list("alias", flat=True)
            )
        field_names.extend(aliases)
        return field_names

    def build_unknown_field(self, field_name, model_class):
        # TODO: get this somewhere else?
        graph_slug = self.__class__.Meta.graph_slug
        node = Node.objects.get(
            graph__slug=graph_slug,
            graph__source_identifier=None,
            alias=field_name,
        )
        model_field = deepcopy(self.DATATYPE_FIELD_MAPPING[node.datatype])
        model_field.model = ResourceInstance
        model_field.blank = not node.isrequired
        if isinstance(model_field, ForeignKey):
            model_field.queryset = ResourceInstance.as_model(graph_slug)
            relation_info = model_meta.RelationInfo(
                model_field=ForeignKey("ResourceInstance", on_delete=DO_NOTHING),
                related_model=ResourceInstance,
                to_many=False,
                to_field=None,
                has_through_model=False,
                reverse=False,
            )
            return self.build_relational_field(field_name, relation_info)
        else:
            return self.build_standard_field(field_name, model_field)


### end code that should go in arches rest framework

### BEGIN application level code


class SchemeSerializer(PythonicModelSerializer):
    class Meta:
        model = ResourceInstance
        graph_slug = "scheme"
        fields = "__all__"


class ConceptSerializer(PythonicModelSerializer):
    class Meta:
        model = ResourceInstance
        graph_slug = "concept"
        fields = "__all__"
